import logging
import os
import shutil
import signal
import sys
import threading
import tkinter as tk
from tkinter import ttk

from ..logic.core import FoxgloveAppLogic
from ..logic.file_explorer_logic import FileExplorerLogic
from ..utils.constants import SETTINGS_FILE_PATH
from ..utils.logger import TkinterLogHandler, get_logger
from ..utils.settings_manager import SettingsManager
from .components.file_explorer_tab import FileExplorerTab
from .components.settings_tab import SettingsTab

logger = get_logger(__name__)


class FoxgloveAppGUIManager:
    def __init__(self, root):
        self.root = root

        logger.info("FoxgloveAppGUIManager initialising")

        self.logic = FoxgloveAppLogic(log_callback=self.log_message)
        self.file_explorer_logic = FileExplorerLogic()

        self.setup_button_styles()

        self.root.title("Triage GUI")

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        self.main_notebook = ttk.Notebook(main_frame)
        self.main_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self._button_map = {}
        self.create_shared_action_buttons(main_frame)
        self.file_explorer_tab = FileExplorerTab(
            self.main_notebook,
            self.root,
            self.logic,
            self.file_explorer_logic,
            self.log_message,
            self._update_button_states,
        )

        self.file_explorer_tab.focus_file_explorer_tab = self.focus_file_explorer_tab

        # ── Ensure nas_dir is pre-seeded before SettingsTab reads the file ──
        _bootstrap = SettingsManager(SETTINGS_FILE_PATH)
        if not _bootstrap.get("nas_dir"):
            initial_path = self.file_explorer_tab.current_explorer_path
            _bootstrap.set("nas_dir", initial_path)
            _bootstrap.save()
            logger.info("Bootstrapped nas_dir to %s", initial_path)

        self.settings_tab = SettingsTab(self.main_notebook, self.logic, self.log_message)

        self.main_notebook.add(self.file_explorer_tab.frame, text="File Explorer")
        self.main_notebook.add(self.settings_tab.frame, text="Settings")

        # Register callbacks for directory changes
        self.settings_tab.on_nas_dir_changed = self.update_file_explorer_nas_dir
        self.settings_tab.on_logging_dir_changed = self.update_file_explorer_logging_dir

        # Initialize logging directory from settings (silent to avoid logging before log widget exists)
        logging_dir = self.settings_tab.get_setting("logging_dir")
        if logging_dir:
            self.file_explorer_tab.update_logging_root(logging_dir, silent=True)

        # --- Shared Components ---
        self.create_shared_log_frame(main_frame)
        self.create_status_bar()

        # Check if NAS directory exists and log error if not (after log widget is created)
        nas_dir = self.settings_tab.get_setting("nas_dir")
        if nas_dir:
            if not os.path.exists(nas_dir):
                self.log_message(
                    f"⚠️ NAS directory not found: {nas_dir} - "
                    "Please check if NAS is mounted or update path in Settings",
                    is_error=True,
                )
            elif not os.path.isdir(nas_dir):
                self.log_message(f"⚠️ NAS path exists but is not a directory: {nas_dir}", is_error=True)
            elif not os.access(nas_dir, os.R_OK):
                self.log_message(
                    f"⚠️ NAS directory exists but is not accessible (permission denied): {nas_dir}", is_error=True
                )
            else:
                # Check if directory is empty (NAS not mounted)
                try:
                    if not os.listdir(nas_dir):
                        self.log_message(
                            f"⚠️ NAS directory is empty: {nas_dir} - "
                            "NAS may not be mounted. Please run 'mount_all_nas' or check network connection.",
                            is_error=True,
                        )
                except Exception as e:
                    self.log_message(f"⚠️ Could not check NAS directory contents: {nas_dir} - {e}", is_error=True)

        # --- Initial State ---
        self._cache_tab_indices()
        self.on_tab_changed()  # Set initial button states
        self.setup_signal_handlers()
        self.setup_keyboard_shortcuts()

        # Bind tab change event
        self.main_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # Update status bar initially
        self.update_status_bar("Ready")

        # Lock minimum window size to prevent shrinking, but allow growth for new content
        self.root.update_idletasks()
        initial_width = self.root.winfo_width()
        initial_height = self.root.winfo_height()
        self.root.minsize(initial_width, initial_height)

    def setup_button_styles(self):
        style = ttk.Style()

        style.configure(
            "Action.TButton",
            background="#A7DCFF",
            foreground="black",
            borderwidth=2,
            focusthickness=3,
            focuscolor="none",
            padding=(6, 4),  # Horizontal padding 6px, vertical padding 4px
        )

        # Hover effect
        style.map(
            "Action.TButton", background=[("active", "#3498DB"), ("disabled", "#BDC3C7")]  # Darker blue on hover
        )  # Gray when disabled

    def create_shared_action_buttons(self, parent_frame):
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.open_file_button = self._create_button(button_frame, "Open File", self.open_selected_file)
        self.copy_path_button = self._create_button(button_frame, "Copy Path", self.copy_selected_path)
        self.open_in_manager_button = self._create_button(button_frame, "File Manager", self.open_in_file_manager)
        self.open_foxglove_button = self._create_button(button_frame, "Foxglove", self.open_with_foxglove)
        self.open_bazel_button = self._create_button(button_frame, "Rosbag Playback", self.open_with_bazel)
        self.launch_bazel_viz_button = self._create_button(button_frame, "Bazel Viz", self.launch_bazel_viz)
        self.build_bazel_button = self._create_button(button_frame, "Build ...", self.run_bazel_build)
        self.show_process_status_button = self._create_button(
            button_frame, "Running Processes", self.show_process_status
        )

        self._button_map = {
            "open_file": self.open_file_button,
            "copy_path": self.copy_path_button,
            "open_with_foxglove": self.open_foxglove_button,
            "open_with_bazel": self.open_bazel_button,
        }

    def create_shared_log_frame(self, parent_frame):
        status_frame = ttk.LabelFrame(parent_frame, text="Log", padding="10")
        status_frame.pack(padx=5, pady=5, fill="both", expand=True)

        log_container = ttk.Frame(status_frame)
        log_container.pack(fill="both", expand=True)

        log_yscrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL)
        log_xscrollbar = ttk.Scrollbar(log_container, orient=tk.HORIZONTAL)

        self.log_text = tk.Text(
            log_container, height=6, wrap=tk.WORD, yscrollcommand=log_yscrollbar.set, state=tk.DISABLED
        )
        self.log_text.tag_config("error", foreground="red")
        log_yscrollbar.config(command=self.log_text.yview)
        log_xscrollbar.config(command=self.log_text.xview)

        log_yscrollbar.pack(side="right", fill="y")
        log_xscrollbar.pack(side="bottom", fill="x")
        self.log_text.pack(side="left", fill="both", expand=True)

        # Attach Tkinter handler so Python logging routes to the GUI widget
        self._tk_log_handler = TkinterLogHandler(self.log_text)
        self._tk_log_handler.setLevel(logging.INFO)
        logging.getLogger("traige_gui").addHandler(self._tk_log_handler)
        logger.debug("TkinterLogHandler attached to log widget")

    def log_message(self, message, is_error=False, clear_first=False):
        """Route *message* through Python logging so it reaches both the log file
        and the in-app GUI widget (via :class:`TkinterLogHandler`).

        During early initialisation (before ``create_shared_log_frame`` has run)
        the ``TkinterLogHandler`` is not yet attached, so messages are captured
        only by the rotating file handler.

        Args:
            message:    Human-readable log text.
            is_error:   When ``True`` the record is logged at ERROR level and
                        displayed in red in the GUI widget.
            clear_first: When ``True``, clears the widget before this message
                         (delegated to :meth:`TkinterLogHandler.set_clear_pending`).
        """
        if clear_first and hasattr(self, "_tk_log_handler"):
            self._tk_log_handler.set_clear_pending()

        if is_error:
            logger.error("%s", message)
        else:
            logger.info("%s", message)

    def launch_bazel_viz(self):
        self.log_message("Launching Bazel Tools Viz...")
        message, error, _ = self.logic.launch_bazel_tools_viz(self.settings_tab.settings)
        if message:
            self.log_message(message)
        if error:
            self.log_message(error, is_error=True)

    def run_bazel_build(self):
        self.log_message("Starting Bazel build (bazel build //...)...")
        self.status_label.config(foreground="red")
        self.show_progress(True)

        self._building = True
        self._show_building_status()

        def build_task():
            message, error = self.logic.run_bazel_build(self.settings_tab.settings)
            self.root.after(0, lambda: self._bazel_build_complete(message, error))

        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()

    def _show_building_status(self, count=0):
        if not hasattr(self, "_building") or not self._building:
            return

        dots = "." * ((count % 3) + 1)
        self.update_status_bar(f"Building{dots}", "")

        self.root.after(400, lambda: self._show_building_status(count + 1))

    def _bazel_build_complete(self, message, error):
        self._building = False
        self.show_progress(False)
        self.status_label.config(foreground="")
        if message:
            self.log_message(message)
        if error:
            self.log_message(error, is_error=True)
            self.update_status_bar("Build failed", "")
        else:
            self.update_status_bar("Build complete", "")

    def run_bazel_clean(self):
        self.log_message("Running Bazel clean...")
        self.update_status_bar("Cleaning...", "")
        self.show_progress(True)

        def clean_task():
            message, error = self.logic.run_bazel_clean(self.settings_tab.settings)
            self.root.after(0, lambda: self._bazel_clean_complete(message, error))

        thread = threading.Thread(target=clean_task, daemon=True)
        thread.start()

    def _bazel_clean_complete(self, message, error):
        self.show_progress(False)
        if message:
            self.log_message(message)
        if error:
            self.log_message(error, is_error=True)
            self.update_status_bar("Clean failed", "")
        else:
            self.update_status_bar("Clean complete", "")

    def show_process_status(self):
        self.log_message("📊 Current Process Status:", clear_first=False)
        status = self.logic.get_process_status()

        if status["total"] == 0:
            self.log_message("   No processes are currently being tracked.")
        else:
            self.log_message(f"   Total: {status['total']} | Running: {status['running']} | Dead: {status['dead']}")

            for proc in status["processes"]:
                status_icon = "🟢" if proc["running"] else "🔴"
                self.log_message(
                    f"   {status_icon} {proc['name']} (PID: {proc['pid']}) - Runtime: {proc['runtime_display']}"
                )

        # Also show if process monitor is running
        monitor_status = (
            "🟢 Active"
            if self.logic._process_monitor_thread and self.logic._process_monitor_thread.is_alive()
            else "🔴 Inactive"
        )
        self.log_message(f"   Process Monitor: {monitor_status}")

    def on_closing(self):
        # Clean up symlink dir if it exists
        symlink_dir = "/tmp/selected_bags_symlinks"
        if os.path.exists(symlink_dir):
            try:
                shutil.rmtree(symlink_dir, ignore_errors=True)
                self.log_message(f"Cleaned up symlink dir: {symlink_dir}")
            except Exception as e:
                self.log_message(f"Error cleaning symlink dir: {e}", is_error=True)
        self.log_message("Terminating launched processes...", clear_first=True)
        termination_log = self.logic.terminate_all_processes()
        self.log_message(termination_log)
        self.root.destroy()

    def setup_signal_handlers(self):
        def handler(signum, frame):
            self.on_closing()
            sys.exit(0)

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions."""
        # Escape - clear selections (already bound)
        self.root.bind("<Escape>", self.clear_all_selections)

        # Ctrl+P - Show process status
        self.root.bind("<Control-p>", lambda e: self.show_process_status())
        self.root.bind("<Control-P>", lambda e: self.show_process_status())

        # Ctrl+F - Open with Foxglove
        self.root.bind(
            "<Control-f>",
            lambda e: self.open_with_foxglove() if self.open_foxglove_button["state"] == tk.NORMAL else None,
        )
        self.root.bind(
            "<Control-F>",
            lambda e: self.open_with_foxglove() if self.open_foxglove_button["state"] == tk.NORMAL else None,
        )

        # Ctrl+B - Open with Bazel
        self.root.bind(
            "<Control-b>", lambda e: self.open_with_bazel() if self.open_bazel_button["state"] == tk.NORMAL else None
        )
        self.root.bind(
            "<Control-B>", lambda e: self.open_with_bazel() if self.open_bazel_button["state"] == tk.NORMAL else None
        )

        # Ctrl+C - Copy path (when button is enabled)
        self.root.bind(
            "<Control-c>", lambda e: self.copy_selected_path() if self.copy_path_button["state"] == tk.NORMAL else None
        )
        self.root.bind(
            "<Control-C>", lambda e: self.copy_selected_path() if self.copy_path_button["state"] == tk.NORMAL else None
        )

        # Ctrl+O - Open file
        self.root.bind(
            "<Control-o>", lambda e: self.open_selected_file() if self.open_file_button["state"] == tk.NORMAL else None
        )
        self.root.bind(
            "<Control-O>", lambda e: self.open_selected_file() if self.open_file_button["state"] == tk.NORMAL else None
        )

        # Ctrl+M - Open in file manager
        self.root.bind("<Control-m>", lambda e: self.open_in_file_manager())
        self.root.bind("<Control-M>", lambda e: self.open_in_file_manager())

        # Ctrl+Q - Quit application
        self.root.bind("<Control-q>", lambda e: self.on_closing())
        self.root.bind("<Control-Q>", lambda e: self.on_closing())

        # F5 - Refresh current view
        self.root.bind("<F5>", lambda e: self.refresh_current_tab())

        # F1 - Show help/shortcuts
        self.root.bind("<F1>", lambda e: self.show_keyboard_shortcuts())

    def create_status_bar(self):
        """Create a status bar at the bottom of the window."""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        # Left side - main status message (larger and bold)
        self.status_label = ttk.Label(
            self.status_frame,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("TkDefaultFont", 11, "bold"),  # Larger and bold
            padding=(8, 6),  # More padding for bigger text area
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Right side - selection info
        self.selection_label = ttk.Label(
            self.status_frame,
            text="No selection",
            relief=tk.SUNKEN,
            anchor=tk.E,
            width=30,
            font=("TkDefaultFont", 10),
            padding=(6, 6),
        )
        self.selection_label.pack(side="right", padx=(5, 0))

        # Progress bar (hidden by default)
        self.progress_bar = ttk.Progressbar(self.status_frame, mode="indeterminate", length=100)
        # Don't pack it yet, will show when needed

    def update_status_bar(self, message, selection_info=None):
        """Update status bar with current information."""
        self.status_label.config(text=message)
        if selection_info:
            self.selection_label.config(text=selection_info)

    def show_progress(self, show=True):
        """Show or hide the progress indicator."""
        if show:
            self.progress_bar.pack(side="right", padx=5)
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()

    def refresh_current_tab(self):
        """Refresh the currently active tab."""
        current_tab_index = self.main_notebook.index(self.main_notebook.select())

        if current_tab_index == self._explorer_tab_index:
            self.file_explorer_tab.refresh_explorer()
            self.update_status_bar("File Explorer refreshed")
        elif current_tab_index == self._settings_tab_index:
            self.update_status_bar("Settings tab active")

    def show_keyboard_shortcuts(self):
        """Display a window with all keyboard shortcuts."""
        shortcuts_window = tk.Toplevel(self.root)
        shortcuts_window.title("Keyboard Shortcuts")
        shortcuts_window.geometry("500x550")

        main_frame = ttk.Frame(shortcuts_window, padding="20")
        main_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(main_frame, text="Keyboard Shortcuts", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 15))

        # Create scrollable frame
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Shortcuts list
        shortcuts = [
            (
                "General",
                [
                    ("Escape", "Clear text selections"),
                    ("Ctrl+Q", "Quit application"),
                    ("F1", "Show this help"),
                    ("F5", "Refresh current tab"),
                ],
            ),
            (
                "File Operations",
                [
                    ("Ctrl+O", "Open selected file"),
                    ("Ctrl+F", "Open with Foxglove"),
                    ("Ctrl+B", "Open with Bazel"),
                    ("Ctrl+C", "Copy file path"),
                    ("Ctrl+M", "Open in file manager"),
                ],
            ),
            (
                "Navigation",
                [
                    ("Enter", "Open folder/file"),
                    ("Backspace", "Go to parent directory"),
                    ("Arrow Keys", "Navigate file lists"),
                    ("Double-Click", "Open file/folder"),
                ],
            ),
            (
                "Process Management",
                [
                    ("Ctrl+P", "Show process status"),
                ],
            ),
            (
                "Text Editing",
                [
                    ("Ctrl+A", "Select all text in entry"),
                ],
            ),
        ]

        for section, items in shortcuts:
            section_label = ttk.Label(scrollable_frame, text=section, font=("Arial", 11, "bold"))
            section_label.pack(anchor="w", pady=(10, 5))

            for key, description in items:
                shortcut_frame = ttk.Frame(scrollable_frame)
                shortcut_frame.pack(fill="x", pady=2)

                key_label = ttk.Label(shortcut_frame, text=key, font=("Courier", 9), width=20)
                key_label.pack(side="left")

                desc_label = ttk.Label(shortcut_frame, text=description)
                desc_label.pack(side="left", padx=(10, 0))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        close_button = ttk.Button(main_frame, text="Close", command=shortcuts_window.destroy)
        close_button.pack(pady=(15, 0))

    def _create_button(self, parent, text, command, state=tk.DISABLED, **pack_opts):
        """Helper to create and pack a ttk.Button with common options."""
        btn = ttk.Button(parent, text=text, command=command, state=state, style="Action.TButton")
        btn.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x", **pack_opts)
        return btn

    # --- Cross-Tab Action Methods ---

    def open_selected_file(self):
        """Open the currently selected file in the explorer tab."""
        if self.main_notebook.index(self.main_notebook.select()) == self._explorer_tab_index:
            self.file_explorer_tab.open_selected_file()

    def open_in_file_manager(self):
        """Open current directory in system file manager via FileExplorerLogic"""
        folder_to_open = self.file_explorer_tab.current_explorer_path

        self.log_message(f"Attempting to open in file manager: {folder_to_open}")

        if folder_to_open and os.path.isdir(folder_to_open):
            success, msg = self.file_explorer_logic.open_in_file_manager(folder_to_open)
            if success:
                self.log_message(msg)
            else:
                self.log_message(msg, is_error=True)
        else:
            self.log_message(f"Folder does not exist: {folder_to_open}", is_error=True)

    def copy_selected_path(self):
        """Copy the path of the selected item from the active tab to the clipboard."""
        current_tab = self.main_notebook.index(self.main_notebook.select())
        item_path = None

        if current_tab == self._explorer_tab_index:
            selection = self.file_explorer_tab.explorer_listbox.curselection()
            if selection:
                # In File Explorer, we only allow copying a single item's path.
                # The button state logic in file_explorer_tab already ensures this.
                idx = selection[0]
                if idx < len(self.file_explorer_tab.explorer_files_list):
                    selected_item = self.file_explorer_tab.explorer_files_list[idx]
                    item_path = os.path.join(self.file_explorer_tab.current_explorer_path, selected_item)

        if item_path:
            success, msg = self.file_explorer_logic.copy_to_clipboard(self.root, item_path)
            if success:
                self.log_message(msg)
            else:
                self.log_message(msg, is_error=True)
        else:
            self.log_message("No single item selected to copy path from.", is_error=True)

    def open_with_foxglove(self):
        """
        Open the selected MCAP file(s) with Foxglove from either tab.
        Optimized for better performance and user feedback.
        """
        current_tab = self.main_notebook.index(self.main_notebook.select())

        mcap_files = []
        if current_tab == self._explorer_tab_index:
            mcap_files = self.file_explorer_tab.get_selected_explorer_mcap_paths()
            if not mcap_files:
                self.log_message("No MCAP file selected in File Explorer.", is_error=True)
                return

        if not mcap_files:
            self.log_message("Open with Foxglove is not available for the current selection.", is_error=True)
            return

        # Show progress indicator for multiple files
        file_count = len(mcap_files)
        if file_count > 5:
            self.show_progress(True)
            self.update_status_bar(f"Loading {file_count} MCAP files...", f"{file_count} files selected")
        else:
            self.update_status_bar("Launching Foxglove...", f"{file_count} file(s) selected")

        # Optimized logging for better user experience
        if file_count == 1:
            file_name = os.path.basename(mcap_files[0])
            self.log_message(f"Launching Foxglove with {file_name}...")
            message, error, _ = self.logic.launch_foxglove(mcap_files[0], self.settings_tab.settings)
        else:
            # Show progress for multiple files
            if file_count <= 5:
                file_names = [os.path.basename(f) for f in mcap_files]
                self.log_message(f"Launching Foxglove with {file_count} files: {', '.join(file_names)}")
            else:
                first_three = ", ".join([os.path.basename(f) for f in mcap_files[:3]])
                self.log_message(f"Launching Foxglove with {file_count} files (showing first 3): {first_three}...")

            message, error, _ = self.logic.launch_foxglove(mcap_files, self.settings_tab.settings)

        # Hide progress and provide feedback
        self.show_progress(False)
        if message:
            self.log_message(message)
            self.update_status_bar("Foxglove launched", f"{file_count} file(s)")
        if error:
            self.log_message(error, is_error=True)
            self.update_status_bar("Error launching Foxglove", f"{file_count} file(s)")

    def open_with_bazel(self):
        """Open the selected MCAP file(s) with Bazel Bag GUI from either tab."""
        current_tab = self.main_notebook.index(self.main_notebook.select())

        mcap_files = []
        if current_tab == self._explorer_tab_index:
            mcap_files = self.file_explorer_tab.get_selected_explorer_mcap_paths()
            if not mcap_files:
                self.log_message("No MCAP file selected in File Explorer.", is_error=True)
                return

        if not mcap_files:
            self.log_message("Open with Bazel is not available for the current selection.", is_error=True)
            return

        # Show progress for multiple files
        file_count = len(mcap_files)
        if file_count > 1:
            self.show_progress(True)
            self.update_status_bar(f"Preparing {file_count} MCAP files...", f"{file_count} files selected")

        if len(mcap_files) == 1:
            self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(mcap_files[0])}...")
            self.update_status_bar("Launching Bazel Bag GUI...", "1 file selected")
            message, error, _ = self.logic.launch_bazel_bag_gui(mcap_files[0], self.settings_tab.settings)
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
        else:
            self.log_message(f"Launching Bazel Bag GUI with {len(mcap_files)} files...")
            self.update_status_bar(f"Loading {file_count} MCAP files...", f"{file_count} files selected")
            message, error, symlink_dir, _ = self.logic.play_bazel_bag_gui_with_symlinks(
                mcap_files, self.settings_tab.settings
            )
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
            else:
                # Show loading animation and check if process is still running
                self._show_loading_status("Bazel Bag GUI")

        # Hide progress
        self.show_progress(False)
        if not error:
            self.update_status_bar("Bazel Bag GUI launched", f"{file_count} file(s)")

    def on_tab_changed(self, event=None):
        """Update file action button states when switching tabs."""
        current_tab_index = self.main_notebook.index(self.main_notebook.select())

        # Disable all buttons first
        self._update_button_states({key: False for key in self._button_map})
        self.open_in_manager_button.config(state=tk.NORMAL)  # This is always available
        self.launch_bazel_viz_button.config(state=tk.NORMAL)  # This is always available
        self.build_bazel_button.config(state=tk.NORMAL)  # This is always available
        self.show_process_status_button.config(state=tk.NORMAL)  # This is always available

        if current_tab_index == self._explorer_tab_index:
            # File Explorer tab: update based on explorer selection (suppress logging to avoid spam)
            self.file_explorer_tab.on_explorer_select(None, suppress_log=True)
        else:
            self._update_button_states({key: False for key in ("open_with_foxglove", "open_with_bazel", "copy_path")})

    def _cache_tab_indices(self):
        """Cache tab indices for performance optimization"""
        try:
            self._explorer_tab_index = self.main_notebook.index(self.file_explorer_tab.frame)
            self._settings_tab_index = self.main_notebook.index(self.settings_tab.frame)
        except tk.TclError:
            self._explorer_tab_index = 0
            self._settings_tab_index = 1

    def _update_button_states(self, states):
        """
        Efficiently update multiple button states in one batch.
        Only updates buttons that actually need to change state.
        """
        state_map = {True: tk.NORMAL, False: tk.DISABLED}

        for state_key, button in self._button_map.items():
            new_state = state_map[states.get(state_key, False)]
            # Only update if state actually changed to reduce UI flicker
            if str(button["state"]) != new_state:
                button.config(state=new_state)

    def clear_all_selections(self, event=None):
        """Clear text selections from all entry widgets"""
        entry_widgets = (self.file_explorer_tab.explorer_path_entry,)

        for widget in entry_widgets:
            if hasattr(widget, "selection_clear"):
                widget.selection_clear()

        for widget in self.settings_tab.get_entry_widgets():
            if hasattr(widget, "selection_clear"):
                widget.selection_clear()

    def _verify_bazel_loaded(self):
        """Verify that Bazel Bag GUI is still running after launch (indicates successful load)"""
        is_running, message = self.logic.check_process_loaded("Bazel Bag GUI")
        if is_running:
            self.log_message(f"✓ {message}")
            self.update_status_bar("Bazel Bag GUI is running", "")
        else:
            self.log_message(f"✗ {message}", is_error=True)
            self.update_status_bar("Bazel Bag GUI failed", "")

    def _show_loading_status(self, process_name, count=0):
        """Show animated loading status and verify process is still running"""
        is_running, message = self.logic.check_process_loaded(process_name)

        if not is_running:
            self.log_message(f"✗ {message}", is_error=True)
            self.update_status_bar(f"{process_name} failed", "")
            # Reset status label color to default
            self.status_label.config(foreground="")
            return

        # Calculate elapsed time
        elapsed_seconds = (count * 300) / 1000  # count * 300ms in seconds

        # Show animated dots (faster animation - 300ms) in green
        dots = "." * ((count % 4) + 1)  # 1-4 dots
        self.status_label.config(foreground="green")
        self.update_status_bar(f"{process_name} loading{dots}", "")

        # Continue polling for 30 seconds max
        if count < 100:  # 100 * 300ms = 30 seconds
            self.root.after(300, lambda: self._show_loading_status(process_name, count + 1))
        else:
            # After 30 seconds, assume loaded and reset color
            self.status_label.config(foreground="")
            self.log_message(f"✓ {process_name} is running (runtime: {int(elapsed_seconds)}s)")
            self.update_status_bar(f"{process_name} is running", "")

    def update_file_explorer_nas_dir(self, new_nas_dir):
        """Update the file explorer's path to match the new NAS directory."""
        self.file_explorer_tab.current_explorer_path = new_nas_dir
        self.file_explorer_tab.refresh_explorer()

    def update_file_explorer_logging_dir(self, new_logging_dir):
        """Update the file explorer's logging directory."""
        self.file_explorer_tab.update_logging_root(new_logging_dir)

    def focus_file_explorer_tab(self):
        """Switch to the File Explorer tab and bring window to front."""
        self.main_notebook.select(self.file_explorer_tab.frame)
        self.root.lift()
        self.root.focus_force()
