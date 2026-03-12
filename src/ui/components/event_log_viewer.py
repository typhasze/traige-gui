"""Event log viewer component for the Triage GUI application.

This module provides :class:`EventLogViewer`, a self-contained widget that
can be embedded in either a :class:`tk.Toplevel` window or a
:class:`ttk.Notebook` tab.  All data loading and timestamp parsing utilities
are exposed as module-level functions so they can be imported independently
(e.g. by :mod:`file_explorer_tab` for MCAP/video look-ups).

Typical usage::

    from src.ui.components.event_log_viewer import EventLogViewer

    viewer = EventLogViewer(
        parent=tab_frame,
        file_path="/path/to/event_log_20250919.txt",
        viewer_id=0,
        on_close=on_close_cb,
        is_tab=True,
        log_message=self.log_message,
        play_video_cb=lambda ts: self.play_video_at_timestamp(fp, ts, viewer_id=vid),
        play_bazel_cb=lambda ts: self.play_bazel_at_timestamp(fp, ts, viewer_id=vid),
        play_bazel_start_cb=lambda ts: self.play_bazel_from_start(fp, ts, viewer_id=vid),
        navigate_mcap_cb=lambda ts: self.navigate_to_mcap_from_timestamp(fp, ts),
    )
    viewer.build_ui()
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

from ...utils.logger import get_logger

logger = get_logger(__name__)

#: Timestamp format strings tried in order during parsing.
TIMESTAMP_FORMATS: List[str] = [
    "%Y-%m-%d %H:%M:%S",  # 2025-09-19 10:50:50
    "%Y-%m-%d-%H-%M-%S",  # 2025-12-16-08-55-17  (MCAP filename format)
    "%Y%m%d_%H%M%S",  # 20250919_093523
    "%Y-%m-%d_%H-%M-%S",  # 2025-09-19_09-35-23
    "%Y%m%d%H%M%S",  # 20250919093523
    "%H:%M:%S",  # 09:35:23  (time-only — assumes today's date)
    "%Y-%m-%d %H:%M:%S.%f",  # 2025-09-19 09:35:23.123456
    "%Y%m%d%H%M%S%f",  # 20250919093523123456  (with microseconds)
]


def normalize_timestamp_str(timestamp_str: str) -> str:
    """Pre-process a raw timestamp string before format-matching.

    Handles MCAP filename prefixes (``PSA8411_2025-12-16-08-55-17_0`` → middle
    part extracted) and trailing millisecond tokens (``2025-09-19 10:50:50 430``).
    """
    # Handle MCAP filename format: PREFIX_TIMESTAMP_SUFFIX
    if "_" in timestamp_str and timestamp_str.count("_") >= 2:
        parts = timestamp_str.split("_")
        if len(parts) >= 3:
            potential_ts = parts[1]
            if "-" in potential_ts and len(potential_ts) >= 10:
                return potential_ts

    # Handle "2025-09-19 10:50:50 430" (trailing millisecond token)
    tokens = timestamp_str.split()
    if len(tokens) == 3:
        return f"{tokens[0]} {tokens[1]}"

    return timestamp_str


def parse_timestamp(
    timestamp_str: str,
    log_fn: Optional[Callable[..., None]] = None,
) -> Optional[datetime]:
    """Parse *timestamp_str* → :class:`~datetime.datetime`, or ``None`` on failure.

    Tries :data:`TIMESTAMP_FORMATS` after normalising with
    :func:`normalize_timestamp_str`. Errors are forwarded to *log_fn* when supplied.
    """
    try:
        if not isinstance(timestamp_str, str):
            timestamp_str = str(timestamp_str)

        timestamp_str = normalize_timestamp_str(timestamp_str.strip())

        for fmt in TIMESTAMP_FORMATS:
            try:
                if fmt == "%H:%M:%S":
                    # Time-only: combine with today's date
                    time_part = datetime.strptime(timestamp_str, fmt).time()
                    return datetime.combine(date.today(), time_part)
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        msg = f"Unknown timestamp format: '{timestamp_str}' (length: {len(timestamp_str)})"
        if log_fn:
            log_fn(msg, is_error=True)
        logger.warning("Unknown timestamp format: %r", timestamp_str)
        return None

    except Exception as exc:
        msg = f"Error parsing timestamp '{timestamp_str}': {exc}"
        if log_fn:
            log_fn(msg, is_error=True)
        logger.exception("Error parsing timestamp %r", timestamp_str)
        return None


# Event log data loading — module-level utility functions
def preprocess_event_log_lines(raw_lines: List[str]) -> List[str]:
    """Strip blank lines and the header row; return lines ready for parsing."""
    result: List[str] = []
    for line in raw_lines:
        stripped = line.rstrip("\n")
        if not stripped.strip():
            continue
        if stripped.lstrip().startswith("current_time"):
            continue  # Skip the column-header row
        result.append(stripped)
    return result


def parse_event_rows(
    data_lines: List[str],
    tree: ttk.Treeview,
) -> List[Tuple[str, ...]]:
    """Parse tab-delimited event rows (with multi-line continuation) into *tree*."""
    all_events: List[Tuple[str, ...]] = []
    current_parts: Optional[List[str]] = None
    batch_count = 0
    BATCH_SIZE = 100

    for line in data_lines:
        try:
            parts = [p.strip() for p in line.split("\t")]

            if current_parts is None:
                if len(parts) >= 5:
                    all_events.append(tuple(parts[:5]))
                    tree.insert("", "end", values=parts[:5])
                    batch_count += 1
                elif parts and (line.startswith("\t") or parts[0] == ""):
                    pass  # Orphaned continuation line — skip silently
                else:
                    current_parts = parts
            else:
                # Continuation line
                if line.startswith("\t") or (parts and parts[0] == ""):
                    if parts and parts[0] == "":
                        parts = parts[1:]
                    current_parts.extend(parts)
                else:
                    # Treat as continuation of the description column
                    if len(current_parts) >= 3 and parts:
                        current_parts[2] = (current_parts[2] + " " + parts[0]).strip()
                        if len(parts) > 1:
                            current_parts.extend(parts[1:])
                    else:
                        current_parts.extend(parts)

                if len(current_parts) >= 5:
                    all_events.append(tuple(current_parts[:5]))
                    tree.insert("", "end", values=current_parts[:5])
                    current_parts = None
                    batch_count += 1

            if batch_count >= BATCH_SIZE:
                tree.update_idletasks()
                batch_count = 0

        except Exception:  # nosec B110
            pass  # Silent skip — avoids log spam for individual malformed lines

    return all_events


def _parse_event_file(file_path: str) -> List[Tuple[str, ...]]:
    """Parse *file_path* into event rows without touching any Tkinter widget.

    Safe to call from a background thread.  Returns a list of 5-element tuples.
    """
    all_events: List[Tuple[str, ...]] = []
    current_parts: Optional[List[str]] = None

    with open(file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    for line in preprocess_event_log_lines(raw_lines):
        try:
            parts = [p.strip() for p in line.split("\t")]
            if current_parts is None:
                if len(parts) >= 5:
                    all_events.append(tuple(parts[:5]))
                elif parts and (line.startswith("\t") or parts[0] == ""):
                    pass
                else:
                    current_parts = parts
            else:
                if line.startswith("\t") or (parts and parts[0] == ""):
                    if parts and parts[0] == "":
                        parts = parts[1:]
                    current_parts.extend(parts)
                else:
                    if len(current_parts) >= 3 and parts:
                        current_parts[2] = (current_parts[2] + " " + parts[0]).strip()
                        if len(parts) > 1:
                            current_parts.extend(parts[1:])
                    else:
                        current_parts.extend(parts)

                if len(current_parts) >= 5:
                    all_events.append(tuple(current_parts[:5]))
                    current_parts = None
        except Exception:  # nosec B110
            pass

    return all_events


def load_events(
    file_path: str,
    tree: ttk.Treeview,
    log_fn: Optional[Callable[..., None]] = None,
) -> List[Tuple[str, ...]]:
    """Parse and load *file_path* into *tree*. Large files (>10 MB) emit a warning."""
    all_events: List[Tuple[str, ...]] = []

    # Warn for large files
    try:
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10 MB
            if log_fn:
                log_fn(
                    f"⚠️ Large event log file ({file_size // (1024 * 1024)} MB) — loading may take a moment...",
                    is_error=False,
                )
    except Exception:  # nosec B110
        pass

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            raw_lines = fh.readlines()

        data_lines = preprocess_event_log_lines(raw_lines)
        all_events = parse_event_rows(data_lines, tree)
        logger.debug("Loaded %d events from %s", len(all_events), file_path)

    except Exception as exc:
        if log_fn:
            log_fn(f"Error reading event log file: {exc}", is_error=True)
        logger.exception("Error reading event log file: %s", file_path)

    return all_events


# EventLogViewer — self-contained viewer widget
class EventLogViewer:
    """Self-contained event log viewer embeddable in a window or notebook tab.

    All state (treeview, search var, events list) is owned by this instance.
    Interaction with the application is via callbacks passed at construction.
    """

    def __init__(
        self,
        parent: tk.Widget,
        file_path: str,
        viewer_id: int,
        on_close: Callable[[], None],
        is_tab: bool = False,
        *,
        log_message: Callable[..., None],
        play_video_cb: Optional[Callable[[str], None]] = None,
        play_bazel_cb: Optional[Callable[[str], None]] = None,
        play_bazel_start_cb: Optional[Callable[[str], None]] = None,
        navigate_mcap_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.parent = parent
        self.file_path = file_path
        self.viewer_id = viewer_id
        self.on_close = on_close
        self.is_tab = is_tab
        self._log_message = log_message
        self._play_video_cb = play_video_cb
        self._play_bazel_cb = play_bazel_cb
        self._play_bazel_start_cb = play_bazel_start_cb
        self._navigate_mcap_cb = navigate_mcap_cb

        # Populated by build_ui()
        self._tree: Optional[ttk.Treeview] = None
        self._search_var: Optional[tk.StringVar] = None
        self._all_events: List[Tuple[str, ...]] = []

    # Public API
    def build_ui(self) -> None:
        """Construct and pack all viewer widgets into :attr:`parent`."""
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(
            main_frame,
            text=f"File: {self.file_path}",
            font=("Arial", 10, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        _sf, search_var, search_entry, filter_result_label = self._create_search_frame(main_frame)
        self._search_var = search_var

        tree = self._create_event_tree(main_frame)
        self._tree = tree

        loading_id = tree.insert("", "end", values=("⏳ Loading events…", "", "", "", ""))

        _bf, buttons, functions, status_label = self._create_action_buttons(main_frame, tree)

        self._setup_event_handlers(tree, buttons)
        update_status = self._setup_filtering(tree, search_var, filter_result_label, status_label)

        self._bind_keyboard_shortcuts(main_frame, search_entry, tree, functions)

        try:
            file_size = os.path.getsize(self.file_path)
            if file_size > 10 * 1024 * 1024 and self._log_message:
                self._log_message(
                    f"⚠️ Large event log file ({file_size // (1024 * 1024)} MB) — loading may take a moment...",
                    is_error=False,
                )
        except Exception:  # nosec B110
            pass

        file_path = self.file_path

        def _apply(events: List[Tuple[str, ...]]) -> None:
            try:
                tree.delete(loading_id)
            except Exception:  # nosec B110
                pass
            for row in events:
                tree.insert("", "end", values=row)
            self._all_events.extend(events)
            logger.debug("Loaded %d events from %s", len(events), file_path)
            update_status()

        def _load() -> None:
            try:
                events = _parse_event_file(file_path)
            except Exception as exc:
                logger.exception("Error reading event log file: %s", file_path)
                if self._log_message:
                    self.parent.after(
                        0,
                        lambda e=exc: self._log_message(f"Error reading event log file: {e}", is_error=True),
                    )
                return
            self.parent.after(0, lambda: _apply(events))

        threading.Thread(target=_load, daemon=True).start()

    def load_events_list(self) -> List[Tuple[str, ...]]:
        """Return the full list of parsed events (empty before :meth:`build_ui`)."""
        return list(self._all_events)

    def filter_events(self, search_text: str) -> None:
        """Programmatically filter the treeview by *search_text* (case-insensitive)."""
        if self._search_var is not None:
            self._search_var.set(search_text)

    def _create_search_frame(
        self,
        parent: tk.Widget,
    ) -> Tuple[ttk.Frame, tk.StringVar, ttk.Entry, ttk.Label]:
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Search/Filter:").pack(side="left", padx=(0, 5))

        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        search_entry.bind("<Control-a>", self._select_all_text)
        search_entry.bind("<Control-A>", self._select_all_text)

        filter_result_label = ttk.Label(search_frame, text="")
        filter_result_label.pack(side="left", padx=(10, 0))

        ttk.Button(
            search_frame,
            text="Clear",
            command=lambda: search_var.set(""),
            style="Action.TButton",
        ).pack(side="left", padx=(5, 0))

        return search_frame, search_var, search_entry, filter_result_label

    def _create_event_tree(self, parent: tk.Widget) -> ttk.Treeview:
        tree_container = ttk.Frame(parent)
        tree_container.pack(fill="both", expand=True)

        columns = ("current_time", "timestamp", "txt_manual", "txt_criticality", "ui_mode")
        tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=14)

        tree.heading("current_time", text="Current Time")
        tree.heading("timestamp", text="Timestamp")
        tree.heading("txt_manual", text="Event Description")
        tree.heading("txt_criticality", text="Criticality")
        tree.heading("ui_mode", text="UI Mode")

        tree.column("current_time", width=180, minwidth=150)
        tree.column("timestamp", width=120, minwidth=100)
        tree.column("txt_manual", width=300, minwidth=200)
        tree.column("txt_criticality", width=150, minwidth=100)
        tree.column("ui_mode", width=100, minwidth=80)

        v_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x", before=tree)

        return tree

    def _create_action_buttons(
        self,
        parent: tk.Widget,
        tree: ttk.Treeview,
    ) -> Tuple[ttk.Frame, dict, dict, ttk.Label]:
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(10, 0))

        def _selected_ts() -> Optional[str]:
            sel = tree.selection()
            if sel:
                vals = tree.item(sel[0])["values"]
                if vals:
                    return str(vals[0])
            return None

        def play_video() -> None:
            if hasattr(tree, "play_video_func"):
                tree.play_video_func()  # type: ignore[attr-defined]

        def play_bazel() -> None:
            ts = _selected_ts()
            if ts and self._play_bazel_cb:
                try:
                    self._play_bazel_cb(ts)
                except Exception as exc:
                    self._log_message(f"Error playing bazel: {exc}", is_error=True)

        def play_bazel_from_start() -> None:
            ts = _selected_ts()
            if ts and self._play_bazel_start_cb:
                try:
                    self._play_bazel_start_cb(ts)
                except Exception as exc:
                    self._log_message(f"Error playing bazel from start: {exc}", is_error=True)

        def show_mcap_in_explorer() -> None:
            ts = _selected_ts()
            if ts and self._navigate_mcap_cb:
                try:
                    self._navigate_mcap_cb(ts)
                except Exception as exc:
                    self._log_message(f"Error navigating to MCAP: {exc}", is_error=True)

        btn_video = ttk.Button(
            button_frame,
            text="Play Video",
            command=play_video,
            state="disabled",
            style="Action.TButton",
        )
        btn_video.pack(side="left", padx=(0, 10))

        btn_bazel = ttk.Button(
            button_frame,
            text="Play Rosbag",
            command=play_bazel,
            state="disabled",
            style="Action.TButton",
        )
        btn_bazel.pack(side="left", padx=(0, 10))

        btn_bazel_start = ttk.Button(
            button_frame,
            text="Rosbag from Start",
            command=play_bazel_from_start,
            state="disabled",
            style="Action.TButton",
        )
        btn_bazel_start.pack(side="left", padx=(0, 10))

        btn_mcap = ttk.Button(
            button_frame,
            text="Locate Rosbag",
            command=show_mcap_in_explorer,
            state="disabled",
            style="Action.TButton",
        )
        btn_mcap.pack(side="left", padx=(0, 10))

        status_label = ttk.Label(button_frame, text="")
        status_label.pack(side="left", padx=(10, 0))

        close_text = "Close Tab"
        ttk.Button(button_frame, text=close_text, command=self.on_close, style="Action.TButton").pack(side="right")

        buttons = {
            "play_video": btn_video,
            "play_bazel": btn_bazel,
            "play_bazel_start": btn_bazel_start,
            "show_mcap": btn_mcap,
        }
        functions = {
            "play_video": play_video,
            "play_bazel": play_bazel,
            "play_bazel_from_start": play_bazel_from_start,
            "show_mcap": show_mcap_in_explorer,
        }
        return button_frame, buttons, functions, status_label

    def _setup_event_handlers(
        self,
        tree: ttk.Treeview,
        buttons: dict,
    ) -> None:

        def on_row_select(event: tk.Event) -> None:  # type: ignore[type-arg]
            sel = tree.selection()
            if sel:
                vals = tree.item(sel[0])["values"]
                if vals:
                    current_time = str(vals[0])
                    self._log_message(f"Selected event: {vals[0]} - {vals[2] if len(vals) > 2 else ''}")
                    if self._play_video_cb:
                        cb = self._play_video_cb
                        tree.play_video_func = lambda _ts=current_time: cb(_ts)  # type: ignore[attr-defined]

        def on_double_click(event: tk.Event) -> None:  # type: ignore[type-arg]
            if hasattr(tree, "play_video_func"):
                tree.play_video_func()  # type: ignore[attr-defined]

        def update_button_states(*_args: object) -> None:
            sel = tree.selection()
            state = "normal" if sel else "disabled"
            for btn in buttons.values():
                btn.config(state=state)
            if not sel:
                buttons["play_video"].config(state="disabled")

        tree.bind("<<TreeviewSelect>>", lambda e: (on_row_select(e), update_button_states()))
        tree.bind("<Double-1>", on_double_click)

    def _setup_filtering(
        self,
        tree: ttk.Treeview,
        search_var: tk.StringVar,
        filter_result_label: ttk.Label,
        status_label: ttk.Label,
    ) -> Callable[[], None]:
        all_events = self._all_events

        def update_status() -> None:
            status_label.config(text=f"Total events: {len(tree.get_children())}")

        def filter_events(*_args: object) -> None:
            search_text = search_var.get().lower().strip()

            for item in tree.get_children():
                tree.delete(item)

            if not search_text:
                for evt in all_events:
                    tree.insert("", "end", values=evt)
                filter_result_label.config(text="")
                update_status()
                return

            filtered = 0
            for evt in all_events:
                if search_text in " ".join(str(c) for c in evt).lower():
                    tree.insert("", "end", values=evt)
                    filtered += 1

            total = len(all_events)
            if filtered == 0:
                filter_result_label.config(text="No matches found", foreground="red")
            else:
                filter_result_label.config(text=f"Showing {filtered} of {total}", foreground="blue")
            update_status()

        search_var.trace_add("write", filter_events)
        return update_status

    def _bind_keyboard_shortcuts(
        self,
        parent: tk.Widget,
        search_entry: ttk.Entry,
        tree: ttk.Treeview,
        functions: dict,
    ) -> None:

        def focus_search(event: tk.Event) -> None:  # type: ignore[type-arg]
            search_entry.focus_set()

        def clear_search_and_focus_tree(event: tk.Event) -> str:  # type: ignore[type-arg]
            if self._search_var is not None:
                self._search_var.set("")
            tree.focus_set()
            return "break"

        def run_shortcut(event: tk.Event, action: Callable[[], None]):  # type: ignore[type-arg]
            if event.widget == search_entry:
                return None
            action()
            return "break"

        def close_tab(event: tk.Event) -> str:  # type: ignore[type-arg]
            self.on_close()
            return "break"

        targets = (parent, search_entry, tree)

        for target in targets:
            for key in ("v", "V"):
                target.bind(f"<{key}>", lambda e, f=functions: run_shortcut(e, f["play_video"]), add="+")
            for key in ("b", "B"):
                target.bind(f"<{key}>", lambda e, f=functions: run_shortcut(e, f["play_bazel"]), add="+")
            for key in ("s", "S", "l", "L"):
                target.bind(f"<{key}>", lambda e, f=functions: run_shortcut(e, f["show_mcap"]), add="+")
            for key in ("c", "C"):
                target.bind(f"<{key}>", lambda e, f=functions: run_shortcut(e, f["play_bazel_from_start"]), add="+")

            target.bind("<Control-f>", focus_search, add="+")
            target.bind("<Control-F>", focus_search, add="+")
            target.bind("/", focus_search, add="+")
            target.bind("<Escape>", clear_search_and_focus_tree, add="+")
            target.bind("<Control-F4>", close_tab, add="+")

    @staticmethod
    def _select_all_text(event: tk.Event) -> str:  # type: ignore[type-arg]
        """Ctrl+A handler for Entry widgets inside the viewer."""
        widget = event.widget
        if isinstance(widget, ttk.Entry):
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
        return "break"
