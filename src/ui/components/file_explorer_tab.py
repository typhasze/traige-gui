import glob
import os
import re
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from ...utils.logger import get_logger
from .event_log_viewer import EventLogViewer, parse_timestamp

logger = get_logger(__name__)


class FileExplorerTab:
    def __init__(
        self,
        parent: ttk.Notebook,
        root: tk.Tk,
        logic: Any,
        file_explorer_logic: Any,
        log_message: Callable[..., None],
        update_button_states: Callable[[Dict[str, bool]], None],
    ) -> None:
        self.frame = ttk.Frame(parent)
        self.notebook = parent  # Store reference to the main notebook for creating tabs
        self.root = root
        self.logic = logic
        self.file_explorer_logic = file_explorer_logic
        self.log_message = log_message
        self._update_button_states = update_button_states
        self.focus_file_explorer_tab = None  # Callback to switch to file explorer tab

        # State
        self._data_root = os.path.expanduser("~/data")
        self._abs_data_root = os.path.abspath(self._data_root)

        # Logging directory will be set from settings
        self._logging_root = None

        self.current_explorer_path = self._data_root
        self.explorer_history = []
        self._history_set = set()
        self.explorer_files_list = []

        # Analyze Link State
        self.analyze_link_filename = None
        self.analyze_link_folder = None

        # Track event log viewers and their associated processes
        self.event_log_viewers = {}  # {window_id: {"window": tk.Toplevel, "processes": []}}
        self._next_viewer_id = 0

        # Track event log viewer tabs: {viewer_id: {"frame": ttk.Frame, "processes": []}}
        self.event_log_viewer_tabs = {}

        # Cache for MCAP file search to avoid repeated os.walk (performance optimization)
        self._mcap_cache = {}  # {rosbags_dir: (timestamp, mcap_files_list)}
        self._mcap_cache_ttl = 60  # Cache for 60 seconds

        # Handle clicks on notebook tabs (✕ to close event-log tabs)
        self.notebook.bind("<Button-1>", self._on_notebook_tab_click, add="+")

        # UI Widgets
        self.create_widgets()
        self.bind_events()

        self.refresh_explorer()

    def create_widgets(self) -> None:
        # Explorer path frame
        path_frame = ttk.Frame(self.frame)
        path_frame.pack(fill="x", padx=5, pady=(5, 1))

        path_label = ttk.Label(path_frame, text="File Path:")
        path_label.pack(side=tk.LEFT, padx=(0, 5))

        self.explorer_path_var = tk.StringVar(value=self.current_explorer_path)
        self.explorer_path_entry = ttk.Entry(path_frame, textvariable=self.explorer_path_var, state="readonly")
        self.explorer_path_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.explorer_path_entry.bind("<FocusIn>", lambda e: e.widget.selection_clear())

        # Navigation buttons
        self.go_home_button = self._create_button(path_frame, "Home", self.go_home_directory, side=tk.LEFT)
        self.go_logging_button = self._create_button(path_frame, "LOGGING", self.go_logging_directory, side=tk.LEFT)
        self.go_back_button = self._create_button(path_frame, "Back", self.go_back, side=tk.LEFT)

        # Analyze Link frame
        link_frame = ttk.Frame(self.frame)
        link_frame.pack(fill="x", padx=5, pady=1)

        link_label = ttk.Label(link_frame, text="Analyze Link:")
        link_label.pack(side=tk.LEFT, padx=(0, 5))

        self.link_var = tk.StringVar()
        self.link_entry = ttk.Entry(link_frame, textvariable=self.link_var)
        self.link_entry.pack(side=tk.LEFT, fill="x", expand=True)

        self.analyze_button = self._create_button(link_frame, "Analyze", self.analyze_link, side=tk.LEFT)
        self.clear_button = self._create_button(link_frame, "Clear", self.clear_link_and_list, side=tk.LEFT)

        # Search frame
        search_frame = ttk.Frame(self.frame)
        search_frame.pack(fill="x", padx=5, pady=(1, 5))

        search_label = ttk.Label(search_frame, text="Search Filter:")
        search_label.pack(side=tk.LEFT, padx=(0, 5))

        self.explorer_search_var = tk.StringVar()
        self.explorer_search_entry = ttk.Entry(search_frame, textvariable=self.explorer_search_var)
        self.explorer_search_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.clear_search_button = self._create_button(search_frame, "Clear", self.clear_explorer_search, side=tk.LEFT)

        # Explorer listbox
        list_frame = ttk.Frame(self.frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.explorer_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, exportselection=False)
        self.explorer_listbox.pack(side=tk.LEFT, fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.explorer_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.explorer_listbox.config(yscrollcommand=scrollbar.set)

    def bind_events(self) -> None:
        self.link_entry.bind("<Return>", lambda e: self.analyze_link())
        self.link_entry.bind("<Control-a>", self.select_all_text)
        self.link_entry.bind("<Control-A>", self.select_all_text)
        self.explorer_path_entry.bind("<Return>", self.navigate_to_path)
        self.explorer_search_var.trace_add("write", self.on_explorer_search)
        self.explorer_search_entry.bind("<Return>", lambda e: self.explorer_listbox.focus_set())
        self.explorer_search_entry.bind("<Control-a>", self.select_all_text)
        self.explorer_search_entry.bind("<Control-A>", self.select_all_text)
        self.explorer_search_entry.bind("<Down>", self.focus_explorer_listbox_down)
        self.explorer_search_entry.bind("<Up>", self.focus_explorer_listbox_up)
        self.explorer_search_entry.bind("<Escape>", self.clear_explorer_search)
        self.explorer_listbox.bind("<<ListboxSelect>>", self.on_explorer_select)
        self.explorer_listbox.bind("<Double-1>", self.on_explorer_double_click)
        self.explorer_listbox.bind("<Return>", self.on_explorer_enter_key)
        self.explorer_listbox.bind("<BackSpace>", self.on_explorer_backspace_key)
        self.explorer_listbox.bind("<Key>", self.on_listbox_keypress)

        # Keyboard shortcut for LOGGING directory (Ctrl+L)
        self.frame.bind_all("<Control-l>", lambda e: self.go_logging_directory())
        self.frame.bind_all("<Control-L>", lambda e: self.go_logging_directory())

    def on_listbox_keypress(self, event):
        """Focus search bar on key press in the listbox."""
        # Check if the key is a regular character (alphanumeric, punctuation, etc.)
        if event.char and event.char.isprintable() and len(event.char) == 1:
            self.explorer_search_entry.focus_set()
            # The character from the event that triggered this is not automatically inserted,
            # so we append it to the search variable.
            current_search = self.explorer_search_var.get()
            self.explorer_search_var.set(current_search + event.char)
            # Move cursor to the end
            self.explorer_search_entry.icursor(tk.END)
            return "break"  # Prevents the default listbox behavior for the key press

    def _create_button(self, parent, text, command, state=tk.NORMAL, **pack_opts):
        btn = ttk.Button(parent, text=text, command=command, state=state, style="Action.TButton")
        btn.pack(padx=2, **pack_opts)
        return btn

    def on_explorer_search(self, *args):
        self.refresh_explorer()

    def refresh_explorer(self, event: Optional[Any] = None) -> None:
        """
        Refresh the file explorer with optimized batch operations.
        Shows busy cursor during operation.
        """
        # Show busy cursor
        original_cursor = self.root.cget("cursor")
        self.root.config(cursor="watch")
        self.root.update_idletasks()

        try:
            # Store current state for comparison
            current_path = self.current_explorer_path
            search_text = self.explorer_search_var.get().strip()

            # Clear previous content efficiently
            self.explorer_listbox.delete(0, tk.END)
            self.explorer_files_list.clear()

            # Clear selection state to ensure proper button state management
            self.explorer_listbox.selection_clear(0, tk.END)

            if not os.path.isdir(current_path):
                self.log_message(f"Invalid directory: {current_path}", is_error=True)
                return

            # Update path display
            self.explorer_path_var.set(current_path)

            # Get directory contents efficiently
            dirs, files = self.file_explorer_logic.list_directory(current_path)

            # Apply search filter if present
            if search_text:
                search_lower = search_text.lower()
                dirs = [d for d in dirs if search_lower in d.lower()]
                files = [f for f in files if search_lower in f.lower()]

            # Prepare batch items for insertion
            batch_items = []

            # Add directories first with folder icon (no stat needed)
            for d in dirs:
                batch_items.append((f"📁 {d}", d))

            # Add files with lazy icon loading (get icon but skip slow stat operations)
            for f in files:
                item_path = os.path.join(current_path, f)
                # Only get icon based on extension, skip stat() for now
                icon = self._get_quick_icon(item_path)
                batch_items.append((f"{icon} {f}", f))

            # Batch insert all items efficiently
            for display_text, original_name in batch_items:
                self.explorer_listbox.insert(tk.END, display_text)
                self.explorer_files_list.append(original_name)

            # Apply lime green highlight to event log files
            for idx, original_name in enumerate(self.explorer_files_list):
                name_lower = original_name.lower()
                if name_lower.startswith("event_log_") and name_lower.endswith(".txt"):
                    self.explorer_listbox.itemconfig(idx, {"bg": "#90EE90"})

            # Update button states after refreshing content
            self.on_explorer_select(suppress_log=True)

        except PermissionError:
            self.log_message(f"Permission denied: {self.current_explorer_path}", is_error=True)
        except Exception as e:
            self.log_message(f"Error refreshing explorer: {e}", is_error=True)
        finally:
            # Always restore cursor
            self.root.config(cursor=original_cursor)

    def _get_quick_icon(self, filepath):
        """Get file icon based on extension only (no stat call for performance)."""
        from ...utils.utils import get_file_icon

        return get_file_icon(filepath)

    def get_selected_explorer_mcap_paths(self):
        """
        Get selected MCAP file paths with optimized list comprehension.
        """
        selection = self.explorer_listbox.curselection()
        if not selection:
            return []

        current_path = self.current_explorer_path
        files_list = self.explorer_files_list

        # Optimized single-pass filtering
        return [
            os.path.join(current_path, files_list[idx])
            for idx in selection
            if (
                idx < len(files_list)
                and os.path.isfile(os.path.join(current_path, files_list[idx]))
                and self.file_explorer_logic.is_mcap_file(files_list[idx])
            )
        ]

    def go_back(self) -> None:
        if self.explorer_history:
            # Clear search filter when navigating back
            self.explorer_search_var.set("")

            # Pop from history and also from the set for consistency
            previous_path = self.explorer_history.pop()
            if previous_path in self._history_set:
                self._history_set.remove(previous_path)

            # Remember the directory we're coming from to highlight it
            current_dir_name = os.path.basename(self.current_explorer_path)
            self.current_explorer_path = previous_path
            self.refresh_explorer()

            # Highlight the directory we came from
            self.highlight_directory_in_explorer(current_dir_name)

    def _add_to_history(self, path):
        """Adds a path to the navigation history if it's not already the last one."""
        if not self.explorer_history or self.explorer_history[-1] != path:
            self.explorer_history.append(path)
            # Limit history size
            if len(self.explorer_history) > 20:
                self.explorer_history.pop(0)
            # Rebuild the set from the list to ensure they are always in sync
            self._history_set = set(self.explorer_history)

    def go_up_directory(self) -> None:
        current = os.path.abspath(self.current_explorer_path)
        if current == self._abs_data_root:
            return
        parent_dir = os.path.dirname(current)
        if os.path.commonpath([parent_dir, self._abs_data_root]) != self._abs_data_root:
            return

        # Remember the directory we're coming from to highlight it
        current_dir_name = os.path.basename(current)
        self._add_to_history(self.current_explorer_path)
        self.current_explorer_path = parent_dir
        self.refresh_explorer()

        # Highlight the directory we came from
        self.highlight_directory_in_explorer(current_dir_name)

    def go_home_directory(self) -> None:
        """Navigate to the home directory, adding the current path to history if it's different."""
        # Clear search filter when going home
        self.explorer_search_var.set("")

        # Add the current valid path to history if it's not the destination (home)
        if self.current_explorer_path != self._data_root:
            self._add_to_history(self.current_explorer_path)

        # Set the current path to home and refresh the view
        self.current_explorer_path = self._data_root
        self.refresh_explorer()

    def update_logging_root(self, new_logging_root: Optional[str], silent: bool = False) -> None:
        """Update the logging root directory path."""
        self._logging_root = new_logging_root
        if not silent:
            self.log_message(f"LOGGING directory updated to: {self._logging_root}")

    def go_logging_directory(self):
        """Navigate to the LOGGING directory."""
        # Clear search filter when navigating to LOGGING
        self.explorer_search_var.set("")

        # Check if the LOGGING directory is configured
        if not self._logging_root:
            self.log_message("LOGGING directory not configured. Please check Settings.", is_error=True)
            return

        # Check if the LOGGING directory exists
        if not os.path.exists(self._logging_root):
            self.log_message(f"LOGGING directory not found: {self._logging_root}", is_error=True)
            self.log_message("Please ensure the LOGGING drive is mounted.", is_error=False)
            return

        # Add current path to history if different
        if self.current_explorer_path != self._logging_root:
            self._add_to_history(self.current_explorer_path)

        # Navigate to LOGGING directory
        self.current_explorer_path = self._logging_root
        self.refresh_explorer()
        self.log_message(f"Navigated to LOGGING directory: {self._logging_root}")

    def browse_directory(self) -> None:
        selected_dir = filedialog.askdirectory(initialdir=self.current_explorer_path)
        if selected_dir:
            self._add_to_history(self.current_explorer_path)
            self.current_explorer_path = selected_dir
            self.refresh_explorer()
            # Auto-open event log if enabled
            self._auto_open_event_log_if_enabled()

    def navigate_to_path(self, event: Optional[Any] = None) -> None:
        new_path = self.explorer_path_var.get().strip()
        if new_path and os.path.isdir(new_path) and new_path != self.current_explorer_path:
            self._add_to_history(self.current_explorer_path)
            self.current_explorer_path = new_path
            self.refresh_explorer()
            # Auto-open event log if enabled
            self._auto_open_event_log_if_enabled()
        else:
            self.log_message(f"Invalid path: {new_path}", is_error=True)
            self.explorer_path_var.set(self.current_explorer_path)

    def explorer_navigate_selected(self):
        selection = self.explorer_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                item_path = os.path.join(self.current_explorer_path, selected_item)
                if os.path.isdir(item_path):
                    self._add_to_history(self.current_explorer_path)
                    self.current_explorer_path = item_path
                    self.refresh_explorer()
                    self.clear_explorer_search()
                    # Auto-open event log if enabled
                    self._auto_open_event_log_if_enabled()
                else:
                    self.open_file(item_path)

    def on_explorer_double_click(self, event):
        self.explorer_navigate_selected()

    def on_explorer_enter_key(self, event):
        self.explorer_navigate_selected()

    def on_explorer_backspace_key(self, event):
        self.go_up_directory()
        self.clear_explorer_search()

    def open_selected_file(self):
        selection = self.explorer_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                if selected_item != "..":
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    if os.path.isdir(item_path):
                        self._add_to_history(self.current_explorer_path)
                        self.current_explorer_path = item_path
                        self.refresh_explorer()
                        self.clear_explorer_search()
                        self._auto_open_event_log_if_enabled()
                    elif os.path.isfile(item_path):
                        self.open_file(item_path)

    def open_file(self, file_path: str) -> None:
        # Check if this is an event_log_*.txt file
        filename = os.path.basename(file_path).lower()
        if filename.startswith("event_log_") and filename.endswith(".txt"):
            self.log_message(f"*unique file opened* - Event log file: {os.path.basename(file_path)}")
            # Open custom event log viewer
            self.open_event_log_viewer(file_path)
            return

        # Default file opening behavior for all other files
        success, msg = self.file_explorer_logic.open_file(file_path)
        if success:
            self.log_message(msg)
        else:
            self.log_message(msg, is_error=True)

    def open_event_log_viewer(self, file_path: str) -> None:
        """Open a custom viewer for event log files, either as window or tab based on settings."""
        try:
            # Check settings to determine if we should open as tab
            settings = self._get_runtime_settings()
            open_as_tab = settings.get("event_log_viewer_as_tab", False)
            self.log_message(f"Opening event log viewer (as_tab={open_as_tab})")

            if open_as_tab:
                self._open_event_log_viewer_as_tab(file_path)
            else:
                self._open_event_log_viewer_as_window(file_path)

        except Exception as e:
            self.log_message(f"Error opening event log viewer: {e}", is_error=True)

    def _open_event_log_viewer_as_tab(self, file_path: str) -> None:
        """Open event log viewer as a new tab in the main notebook."""
        viewer_id = self._next_viewer_id
        self._next_viewer_id += 1

        # Create a new frame for the tab
        tab_frame = ttk.Frame(self.notebook, padding="10")

        # Track this viewer tab
        self.event_log_viewer_tabs[viewer_id] = {"frame": tab_frame, "processes": [], "file_path": file_path}

        # Build the viewer UI in the frame
        def on_close() -> None:
            self._cleanup_viewer_tab(viewer_id)

        EventLogViewer(
            parent=tab_frame,
            file_path=file_path,
            viewer_id=viewer_id,
            on_close=on_close,
            is_tab=True,
            log_message=self.log_message,
            play_video_cb=lambda ts: self.play_video_at_timestamp(file_path, ts, viewer_id=viewer_id),
            play_bazel_cb=lambda ts: self.play_bazel_at_timestamp(file_path, ts, viewer_id=viewer_id),
            play_bazel_start_cb=lambda ts: self.play_bazel_from_start(file_path, ts, viewer_id=viewer_id),
            navigate_mcap_cb=lambda ts: self.navigate_to_mcap_from_timestamp(file_path, ts),
        ).build_ui()

        # Add the tab before Settings so Settings remains rightmost
        tab_title = f"Event Log - {os.path.basename(file_path)[:20]} ✕"
        settings_tab_index = self._get_settings_tab_index()
        if settings_tab_index is not None:
            self.notebook.insert(settings_tab_index, tab_frame, text=tab_title)
        else:
            self.notebook.add(tab_frame, text=tab_title)

        # Switch to the new tab
        self.notebook.select(tab_frame)

        self.log_message(f"Opened event log viewer as tab: {os.path.basename(file_path)}")

    def _get_settings_tab_index(self):
        """Return index of Settings tab if present."""
        try:
            tabs = self.notebook.tabs()
            for index, tab_id in enumerate(tabs):
                if self.notebook.tab(tab_id, "text") == "Settings":
                    return index
        except Exception:
            return None
        return None

    def _on_notebook_tab_click(self, event):
        """Close event-log tabs when clicking their ✕ area."""
        try:
            # Check if we clicked on a tab label
            elem = self.notebook.identify(event.x, event.y)
            if elem != "label":
                return

            # Get the clicked tab
            tab_index = self.notebook.index(f"@{event.x},{event.y}")
            tab_id = self.notebook.tabs()[tab_index]
            tab_text = self.notebook.tab(tab_id, "text")

            # Only handle tabs with ✕ (event log tabs)
            if not tab_text.endswith("✕"):
                return

            # Force geometry update
            self.notebook.update_idletasks()

            # Get bbox
            bbox = self.notebook.bbox(tab_index)

            if bbox and len(bbox) == 4:
                x, y, width, height = bbox
                # If bbox is valid (not all zeros)
                if width > 0:
                    # The ✕ is in the rightmost 25% of the tab
                    close_area_start = x + int(width * 0.75)

                    # If clicking outside the close area, allow normal tab selection
                    if event.x < close_area_start:
                        return
                else:
                    # Fallback: estimate based on character count
                    # Each character is roughly 8 pixels
                    estimated_width = len(tab_text) * 8

                    # Calculate where this tab starts by summing previous tab widths
                    tab_start = 0
                    for i in range(tab_index):
                        prev_text = self.notebook.tab(self.notebook.tabs()[i], "text")
                        tab_start += len(prev_text) * 8 + 10

                    # Close area is rightmost 25% of estimated tab width
                    close_area_start = tab_start + int(estimated_width * 0.75)

                    if event.x < close_area_start:
                        return
            else:
                return

            # Close the tab
            tab_widget = self.notebook.nametowidget(tab_id)

            for viewer_id, viewer_info in list(self.event_log_viewer_tabs.items()):
                if viewer_info.get("frame") == tab_widget:
                    self._cleanup_viewer_tab(viewer_id)
                    return "break"

        except tk.TclError:
            return
        except Exception as e:
            self.log_message(f"Tab close error: {e}", is_error=False)

    def _open_event_log_viewer_as_window(self, file_path: str) -> None:
        """Open event log viewer as a new window (original behavior)."""
        viewer_id = self._next_viewer_id
        self._next_viewer_id += 1

        # Create a new window for the event log viewer
        viewer_window = tk.Toplevel(self.root)
        viewer_window.title(f"Event Log Viewer - {os.path.basename(file_path)}")
        viewer_window.geometry("1000x600")

        # Track this viewer
        self.event_log_viewers[viewer_id] = {"window": viewer_window, "processes": [], "file_path": file_path}

        # Cleanup handler for when viewer closes
        def on_viewer_close() -> None:
            self._cleanup_viewer_processes(viewer_id)
            viewer_window.destroy()

        viewer_window.protocol("WM_DELETE_WINDOW", on_viewer_close)

        # Build the viewer UI in the window via the standalone component
        EventLogViewer(
            parent=viewer_window,
            file_path=file_path,
            viewer_id=viewer_id,
            on_close=on_viewer_close,
            is_tab=False,
            log_message=self.log_message,
            play_video_cb=lambda ts: self.play_video_at_timestamp(file_path, ts, viewer_id=viewer_id),
            play_bazel_cb=lambda ts: self.play_bazel_at_timestamp(file_path, ts, viewer_id=viewer_id),
            play_bazel_start_cb=lambda ts: self.play_bazel_from_start(file_path, ts, viewer_id=viewer_id),
            navigate_mcap_cb=lambda ts: self.navigate_to_mcap_from_timestamp(file_path, ts),
        ).build_ui()

    def _cleanup_viewer_tab(self, viewer_id):
        """Cleanup processes and remove a tab-based event log viewer."""
        if viewer_id in self.event_log_viewer_tabs:
            viewer_info = self.event_log_viewer_tabs[viewer_id]

            # Kill any associated processes
            for proc in viewer_info.get("processes", []):
                try:
                    if proc.poll() is None:  # Process is still running
                        proc.terminate()
                        proc.wait(timeout=2)
                except Exception as e:
                    self.log_message(f"Failed to terminate viewer process cleanly: {e}", is_error=False)

            # Remove the tab from the notebook
            tab_frame = viewer_info["frame"]
            try:
                self.notebook.forget(tab_frame)
                # Select the File Explorer tab (index 0) after closing
                self.notebook.select(0)
            except Exception as e:
                self.log_message(f"Failed to remove event log tab: {e}", is_error=False)

            # Remove from tracking
            del self.event_log_viewer_tabs[viewer_id]
            self.log_message("Closed event log viewer tab")

    def _is_tg_folder(self, folder_name: str) -> bool:
        return bool(re.match(r"^TG-\d+$", folder_name))

    def _is_vehicle_folder(self, folder_name: str) -> bool:
        """Check if a folder name matches PSAXXXX pattern."""
        return bool(re.match(r"^PSA\d+$", folder_name))

    def _get_vehicle_folders(self, path: str) -> List[str]:
        """Get all vehicle folders (PSAXXXX) in the given directory."""
        try:
            if not os.path.isdir(path):
                return []
            dirs, _ = self.file_explorer_logic.list_directory(path)
            return [d for d in dirs if self._is_vehicle_folder(d)]
        except Exception:
            return []

    def _find_event_log_file(self, base_path: str) -> Optional[str]:
        """Find event_log_*.txt file in the logs directory."""
        try:
            logs_path = os.path.join(base_path, "logs")
            if not os.path.isdir(logs_path):
                return None

            # Look for event_log_*.txt files
            for file in os.listdir(logs_path):
                if file.lower().startswith("event_log_") and file.lower().endswith(".txt"):
                    return os.path.join(logs_path, file)
            return None
        except Exception:
            return None

    def _auto_open_event_log_if_enabled(self) -> bool:
        """Auto-open event log for TG folders if the setting is enabled."""
        try:
            # Check if the setting is enabled
            settings = self._get_runtime_settings()
            if not settings.get("auto_open_event_log_for_tg", False):
                return False

            current_folder_name = os.path.basename(self.current_explorer_path)

            # Case 1: We're in a TG-XXXX folder
            if self._is_tg_folder(current_folder_name):
                vehicle_folders = self._get_vehicle_folders(self.current_explorer_path)

                # If there's only one vehicle folder, auto-navigate to it and open event log
                if len(vehicle_folders) == 1:
                    vehicle_path = os.path.join(self.current_explorer_path, vehicle_folders[0])
                    event_log_file = self._find_event_log_file(vehicle_path)

                    if event_log_file:
                        self.log_message(f"Auto-opening event log for {vehicle_folders[0]}...")
                        # Navigate to the logs directory
                        logs_path = os.path.dirname(event_log_file)
                        self._add_to_history(self.current_explorer_path)
                        self.current_explorer_path = logs_path
                        self.refresh_explorer()
                        # Open the event log file after a short delay to ensure UI is updated
                        self.root.after(100, lambda: self.open_event_log_viewer(event_log_file))
                        return True

            # Case 2: We're in a vehicle folder (PSAXXXX) inside a TG-XXXX folder
            elif self._is_vehicle_folder(current_folder_name):
                parent_path = os.path.dirname(self.current_explorer_path)
                parent_folder_name = os.path.basename(parent_path)

                # Check if parent is a TG folder
                if self._is_tg_folder(parent_folder_name):
                    event_log_file = self._find_event_log_file(self.current_explorer_path)

                    if event_log_file:
                        self.log_message(f"Auto-opening event log for {current_folder_name}...")
                        # Navigate to the logs directory
                        logs_path = os.path.dirname(event_log_file)
                        self._add_to_history(self.current_explorer_path)
                        self.current_explorer_path = logs_path
                        self.refresh_explorer()
                        # Open the event log file after a short delay to ensure UI is updated
                        self.root.after(100, lambda: self.open_event_log_viewer(event_log_file))
                        return True

            return False
        except Exception as e:
            self.log_message(f"Error in auto-open event log: {e}", is_error=True)
            return False

    def on_explorer_select(self, event: Optional[Any] = None, suppress_log: bool = False) -> None:
        selection = self.explorer_listbox.curselection()
        states = {"open_file": False, "copy_path": False, "open_with_foxglove": False, "open_with_bazel": False}

        selected_paths = []
        if selection:
            for idx in selection:
                if idx < len(self.explorer_files_list):
                    selected_item = self.explorer_files_list[idx]
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    selected_paths.append(item_path)

            is_multiple = len(selection) > 1
            states = self.file_explorer_logic.get_file_action_states(selected_paths, is_multiple)

        if not suppress_log:
            mcap_files = self.get_selected_explorer_mcap_paths()
            if mcap_files:
                self.log_message(f"Selected {len(mcap_files)} bag(s).", clear_first=False)

        self._update_button_states(states)

    def clear_explorer_search(self, event=None):
        self.explorer_search_var.set("")
        self.refresh_explorer()
        self.explorer_listbox.focus_set()  # Move focus to the listbox
        return "break"

    def _focus_explorer_listbox_move(self, direction, event=None):
        self.explorer_listbox.focus_set()
        cur = self.explorer_listbox.curselection()
        max_idx = self.explorer_listbox.size() - 1
        if cur:
            idx = cur[0] + direction
            idx = max(0, min(idx, max_idx))
        else:
            idx = 0
        self.explorer_listbox.selection_clear(0, tk.END)
        self.explorer_listbox.selection_set(idx)
        self.explorer_listbox.see(idx)
        return "break"

    def focus_explorer_listbox_up(self, event=None):
        return self._focus_explorer_listbox_move(-1, event)

    def focus_explorer_listbox_down(self, event=None):
        return self._focus_explorer_listbox_move(1, event)

    def select_all_text(self, event=None):
        if event and isinstance(event.widget, ttk.Entry):
            event.widget.select_range(0, tk.END)
            event.widget.icursor(tk.END)
        return "break"

    def analyze_link(self):
        link = self.link_var.get()
        if not link:
            self.log_message("Please enter a link to analyze.", is_error=True)
            return

        extracted_remote_folder, mcap_filename = self.logic.extract_info_from_link(link)
        self.analyze_link_folder = extracted_remote_folder
        self.analyze_link_filename = mcap_filename

        if not extracted_remote_folder:
            self.log_message("Could not extract information from link.", is_error=True)
            return

        self.log_message(f"Extracted remote folder: {extracted_remote_folder}")
        if mcap_filename:
            self.log_message(f"MCAP file from link: {mcap_filename}")

        local_folder = self.logic.get_local_folder_path(extracted_remote_folder)
        if not local_folder or not os.path.isdir(local_folder):
            self.log_message(
                f"Error: Local folder does not exist or could not be mapped: {local_folder}", is_error=True
            )
            return

        self.log_message(f"Mapped local folder: {local_folder}")

        # Clear search filter to ensure file is visible
        self.explorer_search_var.set("")

        self.current_explorer_path = local_folder
        self.refresh_explorer()
        # Highlight the file if present - delay to ensure listbox is fully populated
        if mcap_filename:
            self.explorer_listbox.after(150, lambda: self.highlight_file_in_explorer(mcap_filename))

    def clear_link_and_list(self):
        self.link_var.set("")
        self.analyze_link_filename = None
        self.analyze_link_folder = None
        self.current_explorer_path = self._data_root
        self.refresh_explorer()

    def highlight_file_in_explorer(self, filename: str) -> None:
        if not filename:
            return

        try:
            # Safety check: ensure listbox is populated
            if not hasattr(self, "explorer_files_list") or not self.explorer_files_list:
                return

            # Clear previous highlights, restoring lime green for event log files
            listbox_size = self.explorer_listbox.size()
            for idx in range(listbox_size):
                try:
                    name = self.explorer_files_list[idx] if idx < len(self.explorer_files_list) else ""
                    name_lower = name.lower()
                    bg = "#90EE90" if (name_lower.startswith("event_log_") and name_lower.endswith(".txt")) else "white"
                    self.explorer_listbox.itemconfig(idx, {"bg": bg})
                except tk.TclError:
                    pass

            # Try to find and select the file in the explorer listbox
            for idx, fname in enumerate(self.explorer_files_list):
                if fname.lower() == filename.strip().lower():
                    try:
                        self.explorer_listbox.selection_clear(0, tk.END)
                        self.explorer_listbox.selection_set(idx)
                        self.explorer_listbox.see(idx)
                        self.explorer_listbox.itemconfig(idx, {"bg": "yellow"})
                        # Trigger selection handler to update button states
                        self.on_explorer_select(suppress_log=True)
                        # Set focus to listbox for arrow key navigation
                        self.explorer_listbox.focus_set()
                    except tk.TclError as e:
                        self.log_message(f"Warning: Could not highlight file: {e}", is_error=False)
                    break
        except Exception as e:
            self.log_message(f"Error highlighting file: {e}", is_error=False)

    def highlight_directory_in_explorer(self, dirname: str) -> None:
        """Highlight and select a directory by name in the explorer listbox."""
        if not dirname:
            return

        try:
            # Safety check: ensure listbox is populated
            if not hasattr(self, "explorer_files_list") or not self.explorer_files_list:
                return

            # Clear previous highlights, restoring lime green for event log files
            listbox_size = self.explorer_listbox.size()
            for idx in range(listbox_size):
                try:
                    name = self.explorer_files_list[idx] if idx < len(self.explorer_files_list) else ""
                    name_lower = name.lower()
                    bg = "#90EE90" if (name_lower.startswith("event_log_") and name_lower.endswith(".txt")) else "white"
                    self.explorer_listbox.itemconfig(idx, {"bg": bg})
                except tk.TclError:
                    pass

            # Try to find and select the directory in the explorer listbox
            dirname_lower = dirname.strip().lower()
            for idx, fname in enumerate(self.explorer_files_list):
                if fname.lower() == dirname_lower:
                    # Check if this is actually a directory (should be among the first items)
                    item_path = os.path.join(self.current_explorer_path, fname)
                    if os.path.isdir(item_path):
                        try:
                            self.explorer_listbox.selection_clear(0, tk.END)
                            self.explorer_listbox.selection_set(idx)
                            self.explorer_listbox.see(idx)
                            self.explorer_listbox.itemconfig(idx, {"bg": "lightblue"})
                            # Trigger selection handler to update button states
                            self.on_explorer_select(suppress_log=True)
                            # Set focus to listbox for arrow key navigation
                            self.explorer_listbox.focus_set()
                        except tk.TclError as e:
                            self.log_message(f"Warning: Could not highlight directory: {e}", is_error=False)
                        break
        except Exception as e:
            self.log_message(f"Error highlighting directory: {e}", is_error=False)

    def play_video_at_timestamp(self, event_log_path: str, timestamp_str: str, viewer_id: Optional[int] = None) -> None:
        """Play video at the specified timestamp using mpv."""
        try:
            # Parse the timestamp from the event log
            event_time = parse_timestamp(timestamp_str, log_fn=self.log_message)
            if not event_time:
                self.log_message(f"Could not parse timestamp: {timestamp_str}", is_error=True)
                return

            # Find the corresponding video file and calculate offset
            video_file, start_offset = self.find_video_for_timestamp(event_log_path, event_time)
            if not video_file:
                self.log_message("No matching video file found", is_error=True)
                return

            # Launch mpv with the calculated start time
            self.log_message(f"Playing video: {os.path.basename(video_file)} at {start_offset}s")

            settings = self._get_runtime_settings()
            message, error, proc_id = self.logic.launch_mpv_video(video_file, start_offset, settings)

            # Track the process for this viewer (works for both windows and tabs)
            if viewer_id is not None and proc_id is not None:
                if viewer_id in self.event_log_viewers:
                    self.event_log_viewers[viewer_id]["processes"].append(proc_id)
                elif viewer_id in self.event_log_viewer_tabs:
                    self.event_log_viewer_tabs[viewer_id]["processes"].append(proc_id)

            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)

        except Exception as e:
            self.log_message(f"Error playing video: {e}", is_error=True)

    def _get_runtime_settings(self) -> Dict[str, Any]:
        settings = getattr(self.logic, "settings", {})
        if not settings:
            from ...utils.constants import DEFAULT_SETTINGS

            settings = DEFAULT_SETTINGS.copy()
        return settings

    def _cleanup_viewer_processes(self, viewer_id: int) -> None:
        """Clean up processes associated with a specific event log viewer."""
        if viewer_id not in self.event_log_viewers:
            return

        viewer_info = self.event_log_viewers[viewer_id]
        process_ids = viewer_info.get("processes", [])

        if process_ids:
            self.log_message(f"Closing {len(process_ids)} process(es) for event log viewer...")
            for proc_id in process_ids:
                try:
                    self.logic.terminate_process_by_id(proc_id)
                except Exception as e:
                    self.log_message(f"Error terminating process: {e}", is_error=True)

        # Remove viewer from tracking
        del self.event_log_viewers[viewer_id]

    def find_video_for_timestamp(self, event_log_path: str, event_time: datetime) -> Tuple[Optional[str], int]:
        """Find the video file that contains the specified timestamp and calculate offset."""
        try:
            # Extract date from event log path
            # Example: ~/data/20250919/TG-7737/PSA8600/logs -> ~/data/20250919/TG-7737/PSA8600/video
            log_dir = os.path.dirname(event_log_path)
            base_dir = os.path.dirname(log_dir)  # Remove 'logs' part
            video_dir = os.path.join(base_dir, "video")

            if not os.path.exists(video_dir):
                self.log_message(f"Video directory not found: {video_dir}", is_error=True)
                return None, 0

            # Find all video files in the directory
            video_pattern = os.path.join(video_dir, "*.mp4")
            video_files = glob.glob(video_pattern)

            if not video_files:
                self.log_message(f"No video files found in: {video_dir}", is_error=True)
                return None, 0

            # Parse video filenames to find the one that contains our timestamp
            # Video format: 2025-09-19_09-35-23.mp4 (start time of recording)
            best_video = None
            best_start_time = None

            for video_file in video_files:
                filename = os.path.basename(video_file)
                # Extract timestamp from filename (remove .mp4 extension)
                timestamp_part = filename.replace(".mp4", "")

                # Parse video start time
                video_start_time = parse_timestamp(timestamp_part, log_fn=None)
                if video_start_time:
                    # Check if event time is after this video's start time
                    if event_time >= video_start_time:
                        # This could be the right video, but check if there's a later one
                        if best_start_time is None or video_start_time > best_start_time:
                            best_video = video_file
                            best_start_time = video_start_time

            if best_video and best_start_time:
                # Calculate offset in seconds
                time_diff = event_time - best_start_time
                offset_seconds = int(time_diff.total_seconds())

                self.log_message(f"Found video: {os.path.basename(best_video)}, offset: {offset_seconds}s")
                return best_video, offset_seconds
            else:
                self.log_message("No suitable video file found for the timestamp", is_error=True)
                return None, 0

        except Exception as e:
            self.log_message(f"Error finding video for timestamp: {e}", is_error=True)
            return None, 0

    def _get_mcap_files_cached(self, rosbags_dir):
        """
        Get MCAP files from directory with caching to avoid repeated os.walk.
        Cache expires after _mcap_cache_ttl seconds.
        """
        import time

        current_time = time.time()

        # Check cache
        if rosbags_dir in self._mcap_cache:
            cache_time, cached_files = self._mcap_cache[rosbags_dir]
            if current_time - cache_time < self._mcap_cache_ttl:
                return cached_files

        # Cache miss or expired - scan directory
        mcap_files = []
        max_depth = 3
        base_depth = rosbags_dir.count(os.sep)

        try:
            for root, dirs, files in os.walk(rosbags_dir):
                current_depth = root.count(os.sep) - base_depth
                if current_depth >= max_depth:
                    dirs[:] = []

                for file in files:
                    if file.endswith(".mcap"):
                        mcap_files.append(os.path.join(root, file))

                if len(mcap_files) > 100:
                    break
        except Exception:  # nosec B110
            pass  # Silently ignore walk errors (permissions, etc.)

        # Update cache
        self._mcap_cache[rosbags_dir] = (current_time, mcap_files)
        return mcap_files

    def find_mcap_for_timestamp(
        self, event_log_path: str, event_time: Optional[datetime]
    ) -> Tuple[Optional[str], Optional[float]]:
        """Find the MCAP file that contains the specified timestamp.
        If event_time is None, return the first available MCAP file."""
        try:
            # Extract date from event log path
            # Example: ~/data/20250919/TG-7737/PSA8600/logs -> ~/data/20250919/TG-7737/PSA8600/rosbags/default/...
            log_dir = os.path.dirname(event_log_path)
            base_dir = os.path.dirname(log_dir)  # Remove 'logs' part
            rosbags_dir = os.path.join(base_dir, "rosbags", "default")

            if not os.path.exists(rosbags_dir):
                self.log_message(f"Rosbags directory not found: {rosbags_dir}", is_error=True)
                return None, None

            # Use cached MCAP file search for performance
            mcap_files = self._get_mcap_files_cached(rosbags_dir)

            if not mcap_files:
                self.log_message(f"No MCAP files found in: {rosbags_dir}", is_error=True)
                return None, None

            # If no event_time provided, return the first MCAP file (for playing from start)
            if event_time is None:
                # Sort by filename to get a consistent result
                mcap_files.sort()
                self.log_message(f"Using MCAP: {os.path.basename(mcap_files[0])}")
                return mcap_files[0], 0

            # Parse MCAP filenames to find the one that contains our timestamp
            # MCAP format examples: 2025-09-19_09-35-23.mcap or similar
            best_mcap = None
            best_start_time = None

            for mcap_file in mcap_files:
                filename = os.path.basename(mcap_file)
                # Extract timestamp from filename (remove .mcap extension)
                timestamp_part = filename.replace(".mcap", "")

                # Parse MCAP start time
                mcap_start_time = parse_timestamp(timestamp_part, log_fn=None)
                if mcap_start_time:
                    # Check if event time is after this MCAP's start time
                    if event_time >= mcap_start_time:
                        # This could be the right MCAP, but check if there's a later one
                        if best_start_time is None or mcap_start_time > best_start_time:
                            best_mcap = mcap_file
                            best_start_time = mcap_start_time

            if best_mcap and best_start_time:
                # Calculate offset in seconds from bag start
                time_diff = event_time - best_start_time
                offset_seconds = time_diff.total_seconds()

                self.log_message(
                    f"Found MCAP: {os.path.basename(best_mcap)}, approximate offset: {offset_seconds:.1f}s"
                )
                return best_mcap, offset_seconds
            else:
                self.log_message("No suitable MCAP file found for the timestamp", is_error=True)
                return None, None

        except Exception as e:
            self.log_message(f"Error finding MCAP for timestamp: {e}", is_error=True)
            return None, None

    def _find_best_mcap_index(self, mcap_files_with_times: list, event_time) -> int | None:
        """Return the index of the MCAP that should contain *event_time*.

        Iterates *mcap_files_with_times* (a list of ``(path, start_datetime)``
        sorted ascending by start time) and returns the index of the last entry
        whose start time is <= *event_time*, or ``None`` if none qualify.

        Args:
            mcap_files_with_times: Sorted list of ``(path, datetime)`` pairs.
            event_time:            The target :class:`datetime` to locate.

        Returns:
            Integer index into *mcap_files_with_times*, or ``None``.
        """
        target_idx = None
        for idx, (_, start_time) in enumerate(mcap_files_with_times):
            if event_time >= start_time:
                target_idx = idx
        return target_idx

    def find_mcap_with_buffer(
        self, event_log_path: str, event_time: datetime, buffer_seconds: int = 30
    ) -> Tuple[Optional[List[str]], Optional[float]]:
        """Find MCAP files needed to play with a time buffer before the event.

        Returns ``(mcap_files_list, adjusted_offset)`` where *mcap_files_list*
        contains the file(s) needed and *adjusted_offset* is the playback start
        time in seconds within the combined files.

        The buffer look-back is achieved via :meth:`_find_best_mcap_index`.
        """
        try:
            log_dir = os.path.dirname(event_log_path)
            base_dir = os.path.dirname(log_dir)
            rosbags_dir = os.path.join(base_dir, "rosbags", "default")

            if not os.path.exists(rosbags_dir):
                self.log_message(f"Rosbags directory not found: {rosbags_dir}", is_error=True)
                return None, None

            # Build a sorted list of (path, start_datetime) pairs
            mcap_files = self._get_mcap_files_cached(rosbags_dir)
            mcap_files_with_times = []
            for mcap_path in mcap_files:
                filename = os.path.basename(mcap_path)
                start_time = parse_timestamp(filename.replace(".mcap", ""), log_fn=None)
                if start_time:
                    mcap_files_with_times.append((mcap_path, start_time))

            if not mcap_files_with_times:
                self.log_message(f"No MCAP files found in: {rosbags_dir}", is_error=True)
                return None, None

            mcap_files_with_times.sort(key=lambda x: x[1])

            # Locate the MCAP that contains the event
            target_idx = self._find_best_mcap_index(mcap_files_with_times, event_time)
            if target_idx is None:
                self.log_message("No suitable MCAP file found for the timestamp", is_error=True)
                return None, None

            target_mcap, target_start_time = mcap_files_with_times[target_idx]

            # Calculate the desired playback start time (buffer_seconds before event)
            from datetime import timedelta

            buffered_time = event_time - timedelta(seconds=buffer_seconds)

            # If the buffered time falls before the current MCAP, include the previous one
            if target_idx > 0:
                prev_mcap, prev_start_time = mcap_files_with_times[target_idx - 1]
                if buffered_time < target_start_time and buffered_time >= prev_start_time:
                    offset_seconds = (buffered_time - prev_start_time).total_seconds()
                    self.log_message(
                        f"Using MCAPs: {os.path.basename(prev_mcap)} + "
                        f"{os.path.basename(target_mcap)}, offset: {offset_seconds:.1f}s (30s buffer)"
                    )
                    return [prev_mcap, target_mcap], offset_seconds
                elif buffered_time < prev_start_time:
                    self.log_message(
                        f"Buffer time exceeds available data, starting from beginning of "
                        f"{os.path.basename(target_mcap)}"
                    )
                    return [target_mcap], 0

            # Buffer lands within the current MCAP
            offset_seconds = max(0, (buffered_time - target_start_time).total_seconds())
            self.log_message(f"Using MCAP: {os.path.basename(target_mcap)}, offset: {offset_seconds:.1f}s (30s buffer)")
            return [target_mcap], offset_seconds

        except Exception as e:
            self.log_message(f"Error finding MCAP with buffer: {e}", is_error=True)
            logger.exception("Error finding MCAP with buffer for %s", event_log_path)
            return None, None

    def play_bazel_at_timestamp(self, event_log_path: str, timestamp_str: str, viewer_id: Optional[int] = None) -> None:
        """Play rosbag at the specified timestamp using Bazel Bag GUI.
        Starts playback 30 seconds before the event timestamp."""
        try:
            # Parse the timestamp from the event log
            event_time = parse_timestamp(timestamp_str, log_fn=self.log_message)
            if not event_time:
                self.log_message(f"Could not parse timestamp: {timestamp_str}", is_error=True)
                return

            # Find the corresponding MCAP files with 30-second buffer
            mcap_files, start_offset = self.find_mcap_with_buffer(event_log_path, event_time, buffer_seconds=30)
            if not mcap_files:
                self.log_message("No matching MCAP file found", is_error=True)
                return

            # Get settings from the logic's GUI manager (if available)
            try:
                settings = self._get_runtime_settings()
            except (AttributeError, ImportError):
                from ...utils.constants import DEFAULT_SETTINGS

                settings = DEFAULT_SETTINGS.copy()

            # Launch bazel bag gui with the MCAP file(s) and start offset
            if len(mcap_files) > 1:
                # Multiple MCAPs - use symlink playback
                self.log_message(f"Launching Bazel Bag GUI with combined MCAPs at offset {int(start_offset)}s...")
                message, error, symlink_dir, proc_id = self.logic.play_bazel_bag_gui_with_symlinks(
                    mcap_files, settings, start_time=start_offset
                )
            else:
                # Single MCAP - use normal playback
                self.log_message(
                    f"Launching Bazel Bag GUI with {os.path.basename(mcap_files[0])} at offset {int(start_offset)}s..."
                )
                message, error, proc_id = self.logic.launch_bazel_bag_gui(
                    mcap_files[0], settings, start_time=start_offset
                )

            # Track the process for this viewer (works for both windows and tabs)
            if viewer_id is not None and proc_id is not None:
                if viewer_id in self.event_log_viewers:
                    self.event_log_viewers[viewer_id]["processes"].append(proc_id)
                elif viewer_id in self.event_log_viewer_tabs:
                    self.event_log_viewer_tabs[viewer_id]["processes"].append(proc_id)

            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)

        except Exception as e:
            self.log_message(f"Error playing bazel at timestamp: {e}", is_error=True)

    def play_bazel_from_start(self, event_log_path: str, timestamp_str: str, viewer_id: Optional[int] = None) -> None:
        """Play rosbag from the start without seeking to a specific timestamp.
        Uses the timestamp to identify which rosbag file to play."""
        try:
            # Parse the timestamp from the event log to identify the correct MCAP
            event_time = parse_timestamp(timestamp_str, log_fn=self.log_message)
            if not event_time:
                self.log_message(f"Could not parse timestamp: {timestamp_str}", is_error=True)
                return

            # Find the corresponding MCAP file (but we'll play from start, so offset doesn't matter)
            mcap_file, _ = self.find_mcap_for_timestamp(event_log_path, event_time)
            if not mcap_file:
                self.log_message("No matching MCAP file found", is_error=True)
                return

            # Get settings from the logic's GUI manager (if available)
            try:
                settings = self._get_runtime_settings()
            except (AttributeError, ImportError):
                from ...utils.constants import DEFAULT_SETTINGS

                settings = DEFAULT_SETTINGS.copy()

            # Launch bazel bag gui without start offset (play from beginning)
            self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(mcap_file)} from start...")
            message, error, proc_id = self.logic.launch_bazel_bag_gui(mcap_file, settings, start_time=None)

            # Track the process for this viewer (works for both windows and tabs)
            if viewer_id is not None and proc_id is not None:
                if viewer_id in self.event_log_viewers:
                    self.event_log_viewers[viewer_id]["processes"].append(proc_id)
                elif viewer_id in self.event_log_viewer_tabs:
                    self.event_log_viewer_tabs[viewer_id]["processes"].append(proc_id)

            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)

        except Exception as e:
            self.log_message(f"Error playing bazel from start: {e}", is_error=True)

    def navigate_to_mcap_from_timestamp(self, event_log_path: str, timestamp_str: str) -> None:
        """Navigate to the MCAP file in the file explorer based on the timestamp."""
        try:
            # Parse the timestamp from the event log
            event_time = parse_timestamp(timestamp_str, log_fn=self.log_message)
            if not event_time:
                self.log_message(f"Could not parse timestamp: {timestamp_str}", is_error=True)
                return

            # Find the corresponding MCAP file
            mcap_file, start_offset = self.find_mcap_for_timestamp(event_log_path, event_time)
            if not mcap_file:
                self.log_message("No matching MCAP file found", is_error=True)
                return

            # Clear search filter to ensure file is visible
            self.explorer_search_var.set("")

            # Navigate to the directory containing the MCAP file
            mcap_dir = os.path.dirname(mcap_file)
            mcap_filename = os.path.basename(mcap_file)

            # Update the current explorer path
            self.current_explorer_path = mcap_dir
            self.explorer_path_var.set(mcap_dir)

            # Add to history
            self._add_to_history(mcap_dir)

            # Refresh the explorer
            self.refresh_explorer()

            # Select and highlight the MCAP file in the listbox
            self.explorer_listbox.after(100, lambda: self._select_file_in_listbox(mcap_filename))
            self.explorer_listbox.after(150, lambda: self.highlight_file_in_explorer(mcap_filename))

            # Switch to file explorer tab
            if self.focus_file_explorer_tab:
                self.explorer_listbox.after(200, self.focus_file_explorer_tab)

            self.log_message(f"Navigated to MCAP: {mcap_filename} (offset: ~{start_offset:.1f}s)")

        except Exception as e:
            self.log_message(f"Error navigating to MCAP: {e}", is_error=True)

    def _select_file_in_listbox(self, filename):
        """Helper method to select a specific file in the listbox."""
        try:
            # Search for the file in the listbox
            for i in range(self.explorer_listbox.size()):
                item = self.explorer_listbox.get(i)
                if item == filename:
                    self.explorer_listbox.selection_clear(0, tk.END)
                    self.explorer_listbox.selection_set(i)
                    self.explorer_listbox.see(i)
                    self.explorer_listbox.activate(i)
                    # Trigger selection event to update button states
                    self.on_explorer_select(None)
                    break
        except Exception as e:
            self.log_message(f"Error selecting file in listbox: {e}", is_error=True)
