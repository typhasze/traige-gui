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
from .components.tooltip import attach_tooltip

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
        self._button_tooltips = {
            "Open": "Open the selected file or folder.",
            "Copy": "Copy selected path(s) to clipboard. (Ctrl+C)",
            "Manager": "Open the current folder in the system file manager. (Ctrl+M)",
            "Foxglove": "Launch selected MCAP file(s) in Foxglove. (Ctrl+F)",
            "Rosbag": "Launch selected MCAP file(s) in Bazel rosbag playback. (Ctrl+B)",
            "Viz": "Run bazel tools visualization from Bazel working directory.",
            "Topic": "Run topic-gui: bazel run //tools/topic:gui.",
            "Plot": "Run av-plot: bazel run //tools/plot.",
            "Build": "Run bazel build //... in Bazel working directory.",
            "Procs": "Show tracked process status, PID, and runtime. (Ctrl+P)",
        }
        self.create_shared_action_buttons(main_frame)
        self.file_explorer_tab = FileExplorerTab(
            self.main_notebook,
            self.root,
            self.logic,
            self.file_explorer_logic,
            self.log_message,
            self._update_button_states,
            copy_selected_path_cb=self.copy_selected_path,
            open_with_foxglove_cb=self.open_with_foxglove,
            open_with_bazel_cb=self.open_with_bazel,
        )

        self.file_explorer_tab.focus_file_explorer_tab = self.focus_file_explorer_tab

        _bootstrap = SettingsManager(SETTINGS_FILE_PATH)
        if not _bootstrap.get("nas_dir"):
            initial_path = self.file_explorer_tab.current_explorer_path
            _bootstrap.set("nas_dir", initial_path)
            _bootstrap.save()
            logger.info("Bootstrapped nas_dir to %s", initial_path)

        self.settings_tab = SettingsTab(self.main_notebook, self.logic, self.log_message)

        self.main_notebook.add(self.file_explorer_tab.frame, text="File Explorer")
        self.main_notebook.add(self.settings_tab.frame, text="Settings")

        self.settings_tab.on_nas_dir_changed = self.update_file_explorer_nas_dir
        self.settings_tab.on_logging_dir_changed = self.update_file_explorer_logging_dir
        self.settings_tab.on_branch_changed = self._refresh_branch_label
        self.file_explorer_tab.on_directory_changed = self._auto_sync_branch

        logging_dir = self.settings_tab.get_setting("logging_dir")
        if logging_dir:
            self.file_explorer_tab.update_logging_root(logging_dir, silent=True)

        self.create_shared_log_frame(main_frame)
        self.create_status_bar()
        self.root.after(300, self._refresh_branch_label)

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
                try:
                    if not os.listdir(nas_dir):
                        self.log_message(
                            f"⚠️ NAS directory is empty: {nas_dir} - "
                            "NAS may not be mounted. Please run 'mount_all_nas' or check network connection.",
                            is_error=True,
                        )
                except Exception as e:
                    self.log_message(f"⚠️ Could not check NAS directory contents: {nas_dir} - {e}", is_error=True)

        self._cache_tab_indices()
        self.on_tab_changed()
        self.setup_signal_handlers()
        self.setup_keyboard_shortcuts()

        self.main_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.update_status_bar("Ready")
        self._building = False

        self.root.update_idletasks()
        initial_width = self.root.winfo_width()
        initial_height = self.root.winfo_height()
        extra_height = 175
        target_height = initial_height + extra_height
        self.root.geometry(f"{initial_width}x{target_height}")
        self.root.minsize(initial_width, target_height)

    def setup_button_styles(self):
        style = ttk.Style()

        style.configure(
            "Action.TButton",
            background="#A7DCFF",
            foreground="black",
            borderwidth=2,
            focusthickness=3,
            focuscolor="none",
            padding=(4, 4),
        )

        style.map("Action.TButton", background=[("active", "#3498DB"), ("disabled", "#BDC3C7")])

    def create_shared_action_buttons(self, parent_frame):
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.open_file_button = self._create_button(button_frame, "Open", self.open_selected_file)
        self.copy_path_button = self._create_button(button_frame, "Copy", self.copy_selected_path)
        self.open_in_manager_button = self._create_button(button_frame, "Manager", self.open_in_file_manager)
        self.open_foxglove_button = self._create_button(button_frame, "Foxglove", self.open_with_foxglove)
        self.open_bazel_button = self._create_button(button_frame, "Rosbag", self.open_with_bazel)
        self.launch_bazel_viz_button = self._create_button(button_frame, "Viz", self.launch_bazel_viz)
        self.topic_gui_button = self._create_button(button_frame, "Topic", self.launch_topic_gui_tool, state=tk.NORMAL)
        self.av_plot_button = self._create_button(button_frame, "Plot", self.launch_av_plot_tool, state=tk.NORMAL)
        self.build_bazel_button = self._create_button(button_frame, "Build", self.run_bazel_build)
        self.show_process_status_button = self._create_button(button_frame, "Procs", self.show_process_status)

        self._button_map = {
            "open_file": self.open_file_button,
            "copy_path": self.copy_path_button,
            "open_with_foxglove": self.open_foxglove_button,
            "open_with_bazel": self.open_bazel_button,
        }

    def create_shared_log_frame(self, parent_frame):
        status_frame = ttk.LabelFrame(parent_frame, text="Log", padding="10")
        status_frame.pack(padx=5, pady=5, fill="x", expand=False)

        log_container = ttk.Frame(status_frame)
        log_container.pack(fill="x", expand=False)

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
        """Route *message* through Python logging to the log file and GUI widget.

        During early init (before the log widget exists) only the file handler captures messages.
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

    def _launch_extra_bazel_tool(self, tool_name, command):
        self.log_message(f"Launching {tool_name}...")
        message, error, _ = self.logic.launch_bazel_tool(self.settings_tab.settings, command, tool_name)
        if message:
            self.log_message(message)
        if error:
            self.log_message(error, is_error=True)

    def launch_topic_gui_tool(self):
        self._launch_extra_bazel_tool("topic-gui", "bazel run //tools/topic:gui")

    def launch_av_plot_tool(self):
        self._launch_extra_bazel_tool("av-plot", "bazel run //tools/plot")

    def _run_in_thread(self, task):
        threading.Thread(target=task, daemon=True).start()

    def _auto_sync_branch(self, folder: str):
        """Called on every directory change. Silently syncs git branch if build_info*.txt is present."""
        import threading

        working_dir = self.settings_tab.get_setting("bazel_working_dir") or ""
        if not working_dir:
            return

        def _task():
            info, err = self.logic.parse_build_info(folder)
            if err:
                # No build_info found — silent, nothing to do
                return

            commit_hash = info["commit_hash"]
            self.root.after(0, lambda: self.log_message(f"build_info found — checking out {commit_hash[:12]}…"))
            success, msg = self.logic.git_checkout(working_dir, commit_hash)
            self.root.after(0, lambda: self._on_sync_done(success, msg, info))

        threading.Thread(target=_task, daemon=True).start()

    def _on_sync_done(self, success, message, info: dict):
        ref = info.get("revision_short") or info["commit_hash"][:12]
        if success:
            self.log_message(f"Checked out {ref}: {message}")
            git_name = info.get("git_name", "")
            revision_short = info.get("revision_short", ref)
            label = f"{git_name}-{revision_short}" if git_name else revision_short
            self.branch_label.config(text=label)
        else:
            self.log_message(f"Checkout failed: {message}", is_error=True)
            self._refresh_branch_label()
        if hasattr(self, "settings_tab"):
            self.settings_tab._refresh_git_branch()

    def run_bazel_build(self):
        if getattr(self, "_building", False):
            self.log_message("Bazel build is already running.")
            return

        self.log_message("Starting Bazel build (bazel build //...)...")
        self.status_label.config(foreground="red")
        self.show_progress(True)
        self._building = True
        self.build_bazel_button.config(state=tk.DISABLED)
        self._show_building_status()

        def build_task():
            message, error = self.logic.run_bazel_build(self.settings_tab.settings)
            self.root.after(0, lambda: self._bazel_build_complete(message, error))

        self._run_in_thread(build_task)

    def _show_building_status(self, count=0):
        if not hasattr(self, "_building") or not self._building:
            return

        dots = "." * ((count % 3) + 1)
        self.update_status_bar(f"Building{dots}", "")

        self.root.after(400, lambda: self._show_building_status(count + 1))

    def _bazel_build_complete(self, message, error):
        self._building = False
        self.build_bazel_button.config(state=tk.NORMAL)
        self.show_progress(False)
        self.status_label.config(foreground="")
        if message:
            self.log_message(message)
        if error:
            self.log_message(error, is_error=True)
            self.update_status_bar("Build failed", "")
        else:
            self.update_status_bar("Build complete", "")

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
        self.root.bind("<Escape>", lambda e: self.clear_all_selections())
        self.root.bind("<F5>", lambda e: self.refresh_current_tab())
        self.root.bind("<F1>", lambda e: self.show_keyboard_shortcuts())
        self.root.bind("<Control-Tab>", self.cycle_tabs_forward)
        self.root.bind("<Control-ISO_Left_Tab>", self.cycle_tabs_forward)
        self.main_notebook.bind("<Control-Tab>", self.cycle_tabs_forward, add="+")
        self.main_notebook.bind("<Control-ISO_Left_Tab>", self.cycle_tabs_forward, add="+")

        def if_explorer_active(action):
            return lambda e: action() if self.main_notebook.select() == str(self.file_explorer_tab.frame) else None

        ctrl_shortcuts = [
            ("p", lambda e: self.show_process_status()),
            ("f", lambda e: self.open_with_foxglove() if self.open_foxglove_button["state"] == tk.NORMAL else None),
            ("b", lambda e: self.open_with_bazel() if self.open_bazel_button["state"] == tk.NORMAL else None),
            ("m", if_explorer_active(self.open_in_file_manager)),
            ("h", if_explorer_active(self.file_explorer_tab.go_home_directory)),
            ("l", if_explorer_active(self.file_explorer_tab.go_logging_directory)),
            ("q", lambda e: self.on_closing()),
        ]
        for key, cb in ctrl_shortcuts:
            self.root.bind(f"<Control-{key}>", cb)
            self.root.bind(f"<Control-{key.upper()}>", cb)

    def create_status_bar(self):
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        self.status_label = ttk.Label(
            self.status_frame,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("TkDefaultFont", 11, "bold"),
            padding=(8, 6),
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.branch_label = ttk.Label(
            self.status_frame,
            text="branch: —",
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
            width=28,
            font=("TkDefaultFont", 10),
            padding=(6, 6),
        )
        self.branch_label.pack(side="right", padx=(5, 0))

        self.selection_label = ttk.Label(
            self.status_frame,
            text="No selection",
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
            width=20,
            font=("TkDefaultFont", 10),
            padding=(6, 6),
        )
        self.selection_label.pack(side="right", padx=(5, 0))

        self.progress_bar = ttk.Progressbar(self.status_frame, mode="indeterminate", length=100)

    def update_status_bar(self, message, selection_info=None):
        """Update status bar with current information."""
        self.status_label.config(text=message)
        if selection_info:
            self.selection_label.config(text=selection_info)

    def _refresh_branch_label(self):
        """Fetch git branch of Bazel working dir in background and update the status bar label."""
        working_dir = self.settings_tab.get_setting("bazel_working_dir") or ""
        if not working_dir:
            return

        import threading

        def _fetch():
            branch, _ = self.logic.get_git_branch(working_dir)
            text = f"branch: {branch}" if branch else "branch: —"
            self.root.after(0, lambda: self.branch_label.config(text=text))

        threading.Thread(target=_fetch, daemon=True).start()

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

    def cycle_tabs_forward(self, event=None):
        """Move to the next notebook tab, wrapping to the first tab at the end."""
        try:
            tabs = self.main_notebook.tabs()
            if not tabs:
                return "break"
            current_index = self.main_notebook.index(self.main_notebook.select())
            next_index = (current_index + 1) % len(tabs)
            self.main_notebook.select(next_index)
        except tk.TclError:
            return "break"
        return "break"

    def _focus_current_tab_widget(self):
        """Move keyboard focus to a useful widget inside the selected tab."""
        try:
            selected_tab_id = self.main_notebook.select()
            if not selected_tab_id:
                return
            tab_widget = self.main_notebook.nametowidget(selected_tab_id)
        except tk.TclError:
            return

        if tab_widget == self.file_explorer_tab.frame:
            self.root.after_idle(self.file_explorer_tab.focus_for_keyboard_navigation)
            return

        if tab_widget == self.settings_tab.frame:
            entry_widgets = self.settings_tab.get_entry_widgets()
            if entry_widgets:
                self.root.after_idle(entry_widgets[0].focus_set)
            else:
                self.root.after_idle(tab_widget.focus_set)
            return

        def _find_treeview(widget):
            if isinstance(widget, ttk.Treeview):
                return widget
            for child in widget.winfo_children():
                found = _find_treeview(child)
                if found is not None:
                    return found
            return None

        tree = _find_treeview(tab_widget)
        if tree is not None:

            def _focus_tree():
                items = tree.get_children()
                if items and not tree.selection():
                    first_item = items[0]
                    tree.selection_set(first_item)
                    tree.focus(first_item)
                    tree.see(first_item)
                    tree.event_generate("<<TreeviewSelect>>")
                tree.focus_set()

            self.root.after_idle(_focus_tree)
            return

        self.root.after_idle(tab_widget.focus_set)

    def show_keyboard_shortcuts(self):
        """Display a window with all keyboard shortcuts."""
        shortcuts_window = tk.Toplevel(self.root)
        shortcuts_window.title("Keyboard Shortcuts")
        shortcuts_window.geometry("500x550")

        main_frame = ttk.Frame(shortcuts_window, padding="20")
        main_frame.pack(fill="both", expand=True)

        # title_label = ttk.Label(main_frame, text="Keyboard Shortcuts", font=("Arial", 14, "bold"))
        # title_label.pack(pady=(0, 15))

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
                    ("Ctrl+Tab", "Move to next tab (wrap around) and focus it"),
                ],
            ),
            (
                "File Operations",
                [
                    ("Ctrl+F", "Launch Foxglove"),
                    ("Ctrl+B", "Launch Rosbag"),
                    ("Ctrl+C", "Copy selected path(s)"),
                    ("Ctrl+E", "Focus search filter"),
                    ("Ctrl+M", "Open current folder in manager"),
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
                "Event Viewer",
                [
                    ("Ctrl+E or /", "Focus event viewer search"),
                    ("Up/Down", "Move event-row selection"),
                    ("Escape", "Clear search and focus event list"),
                    ("Ctrl+V", "Play video at selected event"),
                    ("Ctrl+B", "Play Bazel at selected event"),
                    ("Ctrl+C", "Play Bazel from start at selected event"),
                    ("Ctrl+L", "Show related MCAP"),
                    ("Ctrl+F4", "Close event viewer tab/window"),
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

        # close_button = ttk.Button(main_frame, text="Close", command=shortcuts_window.destroy)
        # close_button.pack(pady=(15, 0))

    def _create_button(self, parent, text, command, state=tk.DISABLED, **pack_opts):
        """Helper to create and pack a ttk.Button with common options."""
        btn = ttk.Button(parent, text=text, command=command, state=state, style="Action.TButton")
        btn.pack(side=tk.LEFT, padx=4, pady=4, **pack_opts)
        attach_tooltip(btn, self._button_tooltips.get(text, text))
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
        selected_paths = []

        if current_tab == self._explorer_tab_index:
            selection = self.file_explorer_tab.explorer_listbox.curselection()
            for idx in selection:
                if idx < len(self.file_explorer_tab.explorer_files_list):
                    selected_item = self.file_explorer_tab.explorer_files_list[idx]
                    selected_paths.append(os.path.join(self.file_explorer_tab.current_explorer_path, selected_item))

        if selected_paths:
            clipboard_text = "\n".join(selected_paths)
            success, msg = self.file_explorer_logic.copy_to_clipboard(self.root, clipboard_text)
            if success:
                self.log_message(msg)
            else:
                self.log_message(msg, is_error=True)
        else:
            self.log_message("No item selected to copy path from.", is_error=True)

    def _get_selected_mcap_files(self):
        """Return selected MCAP paths from the explorer, or empty list with error logged."""
        files = self.file_explorer_tab.get_selected_explorer_mcap_paths()
        if not files:
            self.log_message("No MCAP file selected in File Explorer.", is_error=True)
        return files

    def open_with_foxglove(self):
        """Open selected MCAP file(s) with Foxglove from the File Explorer tab."""
        if self.main_notebook.index(self.main_notebook.select()) != self._explorer_tab_index:
            self.log_message("Open with Foxglove is not available for the current selection.", is_error=True)
            return
        mcap_files = self._get_selected_mcap_files()
        if not mcap_files:
            return

        file_count = len(mcap_files)
        if file_count > 5:
            self.show_progress(True)
            self.update_status_bar(f"Loading {file_count} MCAP files...", f"{file_count} files selected")
        else:
            self.update_status_bar("Launching Foxglove...", f"{file_count} file(s) selected")

        if file_count == 1:
            self.log_message(f"Launching Foxglove with {os.path.basename(mcap_files[0])}...")
            message, error, _ = self.logic.launch_foxglove(mcap_files[0], self.settings_tab.settings)
        else:
            if file_count <= 5:
                self.log_message(
                    f"Launching Foxglove with {file_count} files: {', '.join(os.path.basename(f) for f in mcap_files)}"
                )
            else:
                first_three = ", ".join(os.path.basename(f) for f in mcap_files[:3])
                self.log_message(f"Launching Foxglove with {file_count} files (showing first 3): {first_three}...")
            message, error, _ = self.logic.launch_foxglove(mcap_files, self.settings_tab.settings)

        self.show_progress(False)
        if message:
            self.log_message(message)
            self.update_status_bar("Foxglove launched", f"{file_count} file(s)")
        if error:
            self.log_message(error, is_error=True)
            self.update_status_bar("Error launching Foxglove", f"{file_count} file(s)")

    def open_with_bazel(self):
        """Open selected MCAP file(s) with Bazel Bag GUI from the File Explorer tab."""
        if self.main_notebook.index(self.main_notebook.select()) != self._explorer_tab_index:
            self.log_message("Open with Bazel is not available for the current selection.", is_error=True)
            return
        mcap_files = self._get_selected_mcap_files()
        if not mcap_files:
            return

        file_count = len(mcap_files)
        if file_count > 1:
            self.show_progress(True)
            self.update_status_bar(f"Preparing {file_count} MCAP files...", f"{file_count} files selected")

        if file_count == 1:
            self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(mcap_files[0])}...")
            self.update_status_bar("Launching Bazel Bag GUI...", "1 file selected")
            message, error, _ = self.logic.launch_bazel_bag_gui(mcap_files[0], self.settings_tab.settings)
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
        else:
            self.log_message(f"Launching Bazel Bag GUI with {file_count} files...")
            self.update_status_bar(f"Loading {file_count} MCAP files...", f"{file_count} files selected")
            message, error, symlink_dir, _ = self.logic.play_bazel_bag_gui_with_symlinks(
                mcap_files, self.settings_tab.settings
            )
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
            else:
                self._show_loading_status("Bazel Bag GUI")

        self.show_progress(False)
        if not error:
            self.update_status_bar("Bazel Bag GUI launched", f"{file_count} file(s)")

    def on_tab_changed(self, event=None):
        current_tab_index = self.main_notebook.index(self.main_notebook.select())

        self._update_button_states({key: False for key in self._button_map})
        self.open_in_manager_button.config(
            state=tk.NORMAL if current_tab_index == self._explorer_tab_index else tk.DISABLED
        )
        self.launch_bazel_viz_button.config(state=tk.NORMAL)
        self.topic_gui_button.config(state=tk.NORMAL)
        self.av_plot_button.config(state=tk.NORMAL)
        self.build_bazel_button.config(state=tk.NORMAL)
        self.show_process_status_button.config(state=tk.NORMAL)

        if current_tab_index == self._explorer_tab_index:
            self.file_explorer_tab.on_explorer_select(None, suppress_log=True)
        else:
            self._update_button_states({key: False for key in ("open_with_foxglove", "open_with_bazel", "copy_path")})

        self._focus_current_tab_widget()

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

    def _show_loading_status(self, process_name, count=0):
        """Show animated loading status and verify the process is still running."""
        is_running, message = self.logic.check_process_loaded(process_name)

        if not is_running:
            self.log_message(f"✗ {message}", is_error=True)
            self.update_status_bar(f"{process_name} failed", "")
            self.status_label.config(foreground="")
            return

        dots = "." * ((count % 4) + 1)
        self.status_label.config(foreground="green")
        self.update_status_bar(f"{process_name} loading{dots}", "")

        if count < 100:  # 100 × 300 ms = 30 s max
            self.root.after(300, lambda: self._show_loading_status(process_name, count + 1))
        else:
            elapsed_seconds = (count * 300) // 1000
            self.status_label.config(foreground="")
            self.log_message(f"✓ {process_name} is running (runtime: {elapsed_seconds}s)")
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
