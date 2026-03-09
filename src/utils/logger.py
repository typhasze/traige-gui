"""
Logging configuration for the Triage GUI application.

Sets up Python's standard logging module with:
- A rotating file handler for persistent logs (~/.traige_gui/logs/)
- An optional Tkinter text-widget handler for in-app display
- A consistent log format shared across all components

Usage (in any module)::

    from ..utils.logger import get_logger
    logger = get_logger(__name__)

    logger.info("Something happened")
    logger.error("Something went wrong: %s", exc)

GUI integration (call once in gui_manager.py after the log widget is created)::

    from ..utils.logger import setup_logging, TkinterLogHandler
    setup_logging()
    handler = TkinterLogHandler(self.log_text)
    logging.getLogger("traige_gui").addHandler(handler)
"""

import logging
import logging.handlers
import os
import queue
import threading
from typing import Optional

# ── Module-level constants ────────────────────────────────────────────────────
LOG_DIR = os.path.expanduser("~/.traige_gui/logs")
LOG_FILE = os.path.join(LOG_DIR, "traige_gui.log")
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB per file
BACKUP_COUNT = 3  # Keep last 3 rotated files
ROOT_LOGGER_NAME = "traige_gui"


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """Configure and return the root ``traige_gui`` logger.

    Creates the log directory if needed and attaches a rotating file handler
    plus a WARNING-level console handler.  Safe to call multiple times — extra
    calls are no-ops once handlers are already attached.

    Args:
        level: Minimum log level for the root logger (default: DEBUG so that
               attached handlers can filter independently).

    Returns:
        The configured root ``traige_gui`` logger instance.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger(ROOT_LOGGER_NAME)
    if root.handlers:
        # Already configured – avoid duplicate handlers on re-import
        return root

    root.setLevel(level)

    # ── Rotating file handler (captures everything DEBUG+) ────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(file_handler)

    # ── Console handler (WARNING+ only, useful during development) ─────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(console_handler)

    root.info("Logging initialised — log file: %s", LOG_FILE)
    return root


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger of the root ``traige_gui`` logger.

    Args:
        name: Typically ``__name__`` of the calling module.  If omitted, the
              root ``traige_gui`` logger itself is returned.

    Returns:
        A ``logging.Logger`` instance.
    """
    if name:
        return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")
    return logging.getLogger(ROOT_LOGGER_NAME)


class TkinterLogHandler(logging.Handler):
    """A logging handler that writes records to a Tkinter ``Text`` widget.

    Error-level (and above) records are displayed in red via the ``'error'``
    tag; all other records use the default widget colour.

    The widget's text content is pruned to *max_lines* to prevent unbounded
    memory growth.

    Call :meth:`set_clear_pending` before emitting a record to clear the
    widget first (equivalent to the ``clear_first`` flag in the old API).

    Args:
        text_widget: A ``tk.Text`` widget with ``'error'`` tag pre-configured.
        max_lines: Maximum number of lines retained in the widget.
    """

    def __init__(self, text_widget, max_lines: int = 500) -> None:
        super().__init__()
        self.text_widget = text_widget
        self.max_lines = max_lines
        self._clear_pending = False
        self._queue: "queue.Queue[tuple[str, bool]]" = queue.Queue()
        self._main_thread_id = threading.main_thread().ident
        self._flush_scheduled = False
        # Keep GUI output concise – full timestamp is in the log file
        self.setFormatter(logging.Formatter("%(message)s"))
        self._schedule_flush()

    def _schedule_flush(self) -> None:
        if self._flush_scheduled:
            return
        self._flush_scheduled = True
        self.text_widget.after(50, self._drain_queue)

    def _drain_queue(self) -> None:
        self._flush_scheduled = False
        widget = self.text_widget
        if not int(widget.winfo_exists()):
            return

        if self._clear_pending:
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.config(state="disabled")
            self._clear_pending = False

        had_items = False
        while True:
            try:
                msg, is_error = self._queue.get_nowait()
            except queue.Empty:
                break

            had_items = True
            widget.config(state="normal")
            prefix = "ERROR: " if is_error else "INFO: "
            tag = "error" if is_error else "info"
            widget.insert("end", f"{prefix}{msg}\n", tag)
            widget.see("end")

        if had_items:
            line_count = int(widget.index("end-1c").split(".")[0])
            if line_count > self.max_lines:
                widget.delete("1.0", f"{line_count - self.max_lines}.0")
            widget.config(state="disabled")

        self._schedule_flush()

    def set_clear_pending(self) -> None:
        """Clear the widget content before the next :meth:`emit` call."""
        self._clear_pending = True
        self._schedule_flush()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            is_error = record.levelno >= logging.ERROR
            self._queue.put((msg, is_error))
            if threading.get_ident() == self._main_thread_id:
                self._drain_queue()
            else:
                self._schedule_flush()
        except Exception:  # noqa: BLE001
            self.handleError(record)
