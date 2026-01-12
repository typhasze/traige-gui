import glob
import os
import subprocess
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk


class FileExplorerTab:
    def __init__(self, parent, root, logic, file_explorer_logic, log_message, update_button_states):
        self.frame = ttk.Frame(parent)
        self.root = root
        self.logic = logic
        self.file_explorer_logic = file_explorer_logic
        self.log_message = log_message
        self._update_button_states = update_button_states

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

        # UI Widgets
        self.create_widgets()
        self.bind_events()

        self.refresh_explorer()

    def create_widgets(self):
        # Explorer path frame
        path_frame = ttk.Frame(self.frame)
        path_frame.pack(fill="x", padx=5, pady=5)

        path_label = ttk.Label(path_frame, text="File Path:")
        path_label.pack(side=tk.LEFT, padx=(0, 5))

        self.explorer_path_var = tk.StringVar(value=self.current_explorer_path)
        self.explorer_path_entry = ttk.Entry(path_frame, textvariable=self.explorer_path_var, state="readonly")
        self.explorer_path_entry.pack(side=tk.LEFT, fill="x", expand=True)

        # Navigation buttons
        self.go_home_button = self._create_button(path_frame, "Home", self.go_home_directory, side=tk.LEFT)
        self.go_logging_button = self._create_button(path_frame, "LOGGING", self.go_logging_directory, side=tk.LEFT)
        self.go_back_button = self._create_button(path_frame, "Back", self.go_back, side=tk.LEFT)

        # Analyze Link frame
        link_frame = ttk.Frame(self.frame)
        link_frame.pack(fill="x", padx=5, pady=5)

        link_label = ttk.Label(link_frame, text="Analyze Link:")
        link_label.pack(side=tk.LEFT, padx=(0, 5))

        self.link_var = tk.StringVar()
        self.link_entry = ttk.Entry(link_frame, textvariable=self.link_var)
        self.link_entry.pack(side=tk.LEFT, fill="x", expand=True)

        self.analyze_button = self._create_button(link_frame, "Analyze", self.analyze_link, side=tk.LEFT)
        self.clear_button = self._create_button(link_frame, "Clear", self.clear_link_and_list, side=tk.LEFT)

        # Search frame
        search_frame = ttk.Frame(self.frame)
        search_frame.pack(fill="x", padx=5, pady=5)

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

    def bind_events(self):
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
        btn = ttk.Button(parent, text=text, command=command, state=state)
        btn.pack(padx=2, **pack_opts)
        return btn

    def on_explorer_search(self, *args):
        self.refresh_explorer()

    def refresh_explorer(self, event=None):
        """
        Refresh the file explorer with optimized batch operations.
        """
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

            # Prepare batch items for insertion with pre-allocated list
            total_items = len(dirs) + len(files)
            batch_items = []
            batch_items.reserve(total_items) if hasattr(batch_items, "reserve") else None

            # Add directories first with folder icon
            for d in dirs:
                batch_items.append((f"📁 {d}", d))

            # Add files with appropriate icons
            for f in files:
                item_path = os.path.join(current_path, f)
                info = self.file_explorer_logic.get_file_info(item_path)
                icon = info.get("icon", "📄")
                batch_items.append((f"{icon} {f}", f))

            # Batch insert all items efficiently
            for display_text, original_name in batch_items:
                self.explorer_listbox.insert(tk.END, display_text)
                self.explorer_files_list.append(original_name)

            # Update button states after refreshing content
            self.on_explorer_select(suppress_log=True)

        except PermissionError:
            self.log_message(f"Permission denied: {self.current_explorer_path}", is_error=True)
        except Exception as e:
            self.log_message(f"Error refreshing explorer: {e}", is_error=True)

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

    def go_back(self):
        if self.explorer_history:
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

    def go_up_directory(self):
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

    def go_home_directory(self):
        """Navigate to the home directory, adding the current path to history if it's different."""
        # Add the current valid path to history if it's not the destination (home)
        if self.current_explorer_path != self._data_root:
            self._add_to_history(self.current_explorer_path)

        # Set the current path to home and refresh the view
        self.current_explorer_path = self._data_root
        self.refresh_explorer()

    def update_logging_root(self, new_logging_root, silent=False):
        """Update the logging root directory path."""
        self._logging_root = new_logging_root
        if not silent:
            self.log_message(f"LOGGING directory updated to: {self._logging_root}")

    def go_logging_directory(self):
        """Navigate to the LOGGING directory."""
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

    def browse_directory(self):
        selected_dir = filedialog.askdirectory(initialdir=self.current_explorer_path)
        if selected_dir:
            self._add_to_history(self.current_explorer_path)
            self.current_explorer_path = selected_dir
            self.refresh_explorer()

    def navigate_to_path(self, event=None):
        new_path = self.explorer_path_var.get().strip()
        if new_path and os.path.isdir(new_path) and new_path != self.current_explorer_path:
            self._add_to_history(self.current_explorer_path)
            self.current_explorer_path = new_path
            self.refresh_explorer()
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
                    if os.path.isfile(item_path):
                        self.open_file(item_path)

    def open_file(self, file_path):
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

    def open_event_log_viewer(self, file_path):
        """Open a custom viewer for event log files."""
        try:
            # Create a new window for the event log viewer
            viewer_window = tk.Toplevel(self.root)
            viewer_window.title(f"Event Log Viewer - {os.path.basename(file_path)}")
            viewer_window.geometry("1000x600")

            # Create main frame
            main_frame = ttk.Frame(viewer_window, padding="10")
            main_frame.pack(fill="both", expand=True)

            # File info label
            info_label = ttk.Label(main_frame, text=f"File: {file_path}", font=("Arial", 10, "bold"))
            info_label.pack(anchor="w", pady=(0, 10))

            # Search/Filter frame
            search_frame = ttk.Frame(main_frame)
            search_frame.pack(fill="x", pady=(0, 10))

            search_label = ttk.Label(search_frame, text="Search/Filter:")
            search_label.pack(side="left", padx=(0, 5))

            search_var = tk.StringVar()
            search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
            search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

            # Filter result label
            filter_result_label = ttk.Label(search_frame, text="")
            filter_result_label.pack(side="left", padx=(10, 0))

            # Create scrollbars and treeview with proper layout
            tree_container = ttk.Frame(main_frame)
            tree_container.pack(fill="both", expand=True)

            # Define columns
            columns = ("current_time", "timestamp", "txt_manual", "txt_criticality", "ui_mode")

            # Create treeview
            tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=20)

            # Configure column headings and widths
            tree.heading("current_time", text="Current Time")
            tree.heading("timestamp", text="Timestamp")
            tree.heading("txt_manual", text="Event Description")
            tree.heading("txt_criticality", text="Criticality")
            tree.heading("ui_mode", text="UI Mode")

            # Set column widths
            tree.column("current_time", width=180, minwidth=150)
            tree.column("timestamp", width=120, minwidth=100)
            tree.column("txt_manual", width=300, minwidth=200)
            tree.column("txt_criticality", width=150, minwidth=100)
            tree.column("ui_mode", width=100, minwidth=80)

            # Create scrollbars
            v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=tree.yview)
            h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

            # Pack treeview and vertical scrollbar
            tree.pack(side="left", fill="both", expand=True)
            v_scrollbar.pack(side="right", fill="y")

            # Pack horizontal scrollbar at bottom of same container
            h_scrollbar.pack(side="bottom", fill="x", before=tree)

            # Store for all event data (for filtering)
            all_events = []

            # Parse and load the event log data
            all_events = self.load_event_log_data(tree, file_path)

            # Add selection handler
            def on_row_select(event):
                selected_items = tree.selection()
                if selected_items:
                    item = selected_items[0]
                    values = tree.item(item)["values"]
                    if values and len(values) >= 1:
                        current_time = values[0]  # current_time is in column 0
                        self.log_message(f"Selected event: {values[0]} - {values[2] if len(values) > 2 else ''}")

                        # Add double-click or button to play video
                        def play_video():
                            try:
                                self.play_video_at_timestamp(file_path, current_time)
                            except Exception as e:
                                self.log_message(f"Error playing video: {e}", is_error=True)

                        # Store the play_video function for potential button use
                        tree.play_video_func = play_video

            # Add double-click handler for video playback
            def on_double_click(event):
                if hasattr(tree, "play_video_func"):
                    tree.play_video_func()

            # Add buttons frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill="x", pady=(10, 0))

            # Play Video button
            play_video_button = ttk.Button(
                button_frame,
                text="Play Video at Selected Time",
                command=lambda: getattr(tree, "play_video_func", lambda: None)(),
                state="disabled",
            )
            play_video_button.pack(side="left", padx=(0, 10))

            # Play Bazel button
            def play_bazel():
                selected_items = tree.selection()
                if selected_items:
                    item = selected_items[0]
                    values = tree.item(item)["values"]
                    if values and len(values) >= 1:
                        current_time = values[0]
                        try:
                            self.play_bazel_at_timestamp(file_path, current_time)
                        except Exception as e:
                            self.log_message(f"Error playing bazel: {e}", is_error=True)

            play_bazel_button = ttk.Button(
                button_frame, text="Play Bazel at Selected Time", command=play_bazel, state="disabled"
            )
            play_bazel_button.pack(side="left", padx=(0, 10))

            # Show MCAP in Explorer button
            def show_mcap_in_explorer():
                selected_items = tree.selection()
                if selected_items:
                    item = selected_items[0]
                    values = tree.item(item)["values"]
                    if values and len(values) >= 1:
                        current_time = values[0]
                        try:
                            self.navigate_to_mcap_from_timestamp(file_path, current_time)
                        except Exception as e:
                            self.log_message(f"Error navigating to MCAP: {e}", is_error=True)

            show_mcap_button = ttk.Button(
                button_frame, text="Show MCAP in Explorer", command=show_mcap_in_explorer, state="disabled"
            )
            show_mcap_button.pack(side="left", padx=(0, 10))

            # Update play button state based on selection
            def update_play_button(*args):
                selected_items = tree.selection()
                if selected_items:
                    if hasattr(tree, "play_video_func"):
                        play_video_button.config(state="normal")
                    play_bazel_button.config(state="normal")
                    show_mcap_button.config(state="normal")
                else:
                    play_video_button.config(state="disabled")
                    play_bazel_button.config(state="disabled")
                    show_mcap_button.config(state="disabled")

            tree.bind("<<TreeviewSelect>>", lambda e: (on_row_select(e), update_play_button()))
            tree.bind("<Double-1>", on_double_click)

            close_button = ttk.Button(button_frame, text="Close", command=viewer_window.destroy)
            close_button.pack(side="right")

            # Status label showing number of events
            status_label = ttk.Label(button_frame, text="")
            status_label.pack(side="left")

            # Filter function
            def filter_events(*args):
                search_text = search_var.get().lower().strip()

                # Clear current tree
                for item in tree.get_children():
                    tree.delete(item)

                # If no search text, show all events
                if not search_text:
                    for event in all_events:
                        tree.insert("", "end", values=event)
                    filter_result_label.config(text="")
                    update_status()
                    return

                # Filter events - search across all columns
                filtered_count = 0
                for event in all_events:
                    # Check if search text appears in any column
                    event_text = " ".join(str(col) for col in event).lower()
                    if search_text in event_text:
                        tree.insert("", "end", values=event)
                        filtered_count += 1

                # Update filter result label
                if filtered_count == 0:
                    filter_result_label.config(text="No matches found", foreground="red")
                else:
                    total = len(all_events)
                    filter_result_label.config(text=f"Showing {filtered_count} of {total}", foreground="blue")

                update_status()

            # Bind search to text changes
            search_var.trace_add("write", filter_events)

            # Add clear search button
            clear_search_button = ttk.Button(search_frame, text="Clear", command=lambda: search_var.set(""))
            clear_search_button.pack(side="left", padx=(5, 0))

            # Update status with row count
            def update_status():
                row_count = len(tree.get_children())
                status_label.config(text=f"Total events: {row_count}")

            viewer_window.after(100, update_status)  # Update after data is loaded

            # Keyboard shortcuts for event log viewer
            def on_key_v(event):
                if hasattr(tree, "play_video_func"):
                    tree.play_video_func()

            def on_key_b(event):
                play_bazel()

            def on_key_s(event):
                show_mcap_in_explorer()

            def on_key_f(event):
                search_entry.focus_set()

            # Bind keyboard shortcuts
            viewer_window.bind("<v>", on_key_v)
            viewer_window.bind("<V>", on_key_v)
            viewer_window.bind("<b>", on_key_b)
            viewer_window.bind("<B>", on_key_b)
            viewer_window.bind("<s>", on_key_s)
            viewer_window.bind("<S>", on_key_s)
            viewer_window.bind("<Control-f>", on_key_f)
            viewer_window.bind("<Control-F>", on_key_f)
            viewer_window.bind("/", on_key_f)  # Vim-style search

        except Exception as e:
            self.log_message(f"Error opening event log viewer: {e}", is_error=True)

    def load_event_log_data(self, tree, file_path):
        """Parse and load event log data into the treeview. Returns list of all events."""
        all_events = []
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()

            # Skip the header line if it exists
            data_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("current_time"):  # Skip header
                    data_lines.append(line)

            # Parse each data line
            for line_num, line in enumerate(data_lines, 1):
                try:
                    # Split by tab character
                    parts = line.split("\t")
                    if len(parts) >= 5:
                        # Clean up the parts (remove extra whitespace)
                        parts = [part.strip() for part in parts]

                        # Store event data
                        all_events.append(parts[:5])

                        # Insert into treeview
                        tree.insert("", "end", values=parts[:5])
                    else:
                        self.log_message(f"Skipping malformed line {line_num}: {line}", is_error=True)

                except Exception as e:
                    self.log_message(f"Error parsing line {line_num}: {e}", is_error=True)

        except Exception as e:
            self.log_message(f"Error reading event log file: {e}", is_error=True)

        return all_events

    def on_explorer_select(self, event=None, suppress_log=False):
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

        if not extracted_remote_folder or not mcap_filename:
            self.log_message("Could not extract information from link.", is_error=True)
            return

        self.log_message(f"Extracted remote folder: {extracted_remote_folder}")
        self.log_message(f"MCAP file from link: {mcap_filename}")

        local_folder = self.logic.get_local_folder_path(extracted_remote_folder)
        if not local_folder or not os.path.isdir(local_folder):
            self.log_message(
                f"Error: Local folder does not exist or could not be mapped: {local_folder}", is_error=True
            )
            return

        self.log_message(f"Mapped local folder: {local_folder}")
        self.current_explorer_path = local_folder
        self.refresh_explorer()
        # Highlight the file if present
        self.highlight_file_in_explorer(mcap_filename)

    def clear_link_and_list(self):
        self.link_var.set("")
        self.analyze_link_filename = None
        self.analyze_link_folder = None
        self.current_explorer_path = self._data_root
        self.refresh_explorer()

    def highlight_file_in_explorer(self, filename):
        if not filename:
            return
        # Clear previous highlights
        for idx in range(self.explorer_listbox.size()):
            self.explorer_listbox.itemconfig(idx, {"bg": "white"})
        # Try to find and select the file in the explorer listbox
        for idx, fname in enumerate(self.explorer_files_list):
            if fname.lower() == filename.strip().lower():
                self.explorer_listbox.selection_clear(0, tk.END)
                self.explorer_listbox.selection_set(idx)
                self.explorer_listbox.see(idx)
                self.explorer_listbox.itemconfig(idx, {"bg": "yellow"})
                # Trigger selection handler to update button states
                self.on_explorer_select(suppress_log=True)
                # Set focus to listbox for arrow key navigation
                self.explorer_listbox.focus_set()
                break

    def highlight_directory_in_explorer(self, dirname):
        """Highlight and select a directory by name in the explorer listbox."""
        if not dirname:
            return

        # Clear previous highlights
        for idx in range(self.explorer_listbox.size()):
            self.explorer_listbox.itemconfig(idx, {"bg": "white"})

        # Try to find and select the directory in the explorer listbox
        dirname_lower = dirname.strip().lower()
        for idx, fname in enumerate(self.explorer_files_list):
            if fname.lower() == dirname_lower:
                # Check if this is actually a directory (should be among the first items)
                item_path = os.path.join(self.current_explorer_path, fname)
                if os.path.isdir(item_path):
                    self.explorer_listbox.selection_clear(0, tk.END)
                    self.explorer_listbox.selection_set(idx)
                    self.explorer_listbox.see(idx)
                    self.explorer_listbox.itemconfig(idx, {"bg": "lightblue"})
                    # Trigger selection handler to update button states
                    self.on_explorer_select(suppress_log=True)
                    # Set focus to listbox for arrow key navigation
                    self.explorer_listbox.focus_set()
                    break

    def play_video_at_timestamp(self, event_log_path, timestamp_str):
        """Play video at the specified timestamp using mpv."""
        try:
            # Parse the timestamp from the event log
            event_time = self.parse_timestamp(timestamp_str)
            if not event_time:
                self.log_message(f"Could not parse timestamp: {timestamp_str}", is_error=True)
                return

            # Find the corresponding video file and calculate offset
            video_file, start_offset = self.find_video_for_timestamp(event_log_path, event_time)
            if not video_file:
                self.log_message("No matching video file found", is_error=True)
                return

            # Launch mpv with the calculated start time
            cmd = ["mpv", f"--start={start_offset}", video_file]
            self.log_message(f"Playing video: {os.path.basename(video_file)} at {start_offset}s")

            # Run mpv in background
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        except Exception as e:
            self.log_message(f"Error playing video: {e}", is_error=True)

    def parse_timestamp(self, timestamp_str):
        """Parse timestamp string to datetime object."""
        try:
            # Convert to string if it's not already
            if not isinstance(timestamp_str, str):
                timestamp_str = str(timestamp_str)

            # Clean the timestamp string
            timestamp_str = timestamp_str.strip()

            # Handle MCAP filename format: PSA8411_2025-12-16-08-55-17_0
            # Extract just the timestamp part (remove prefix and suffix)
            if "_" in timestamp_str and timestamp_str.count("_") >= 2:
                parts = timestamp_str.split("_")
                # Check if this looks like: PREFIX_TIMESTAMP_SUFFIX
                if len(parts) >= 3:
                    # Try to parse the middle part as timestamp
                    potential_timestamp = parts[1]
                    if "-" in potential_timestamp and len(potential_timestamp) >= 10:
                        timestamp_str = potential_timestamp

            # Handle the specific format: "2025-09-19 10:50:50 430"
            # where the last part is milliseconds
            if len(timestamp_str.split()) == 3:
                parts = timestamp_str.split()
                if len(parts) == 3:
                    date_part = parts[0]  # 2025-09-19
                    time_part = parts[1]  # 10:50:50
                    # Ignore milliseconds part for now
                    timestamp_str = f"{date_part} {time_part}"

            # Common timestamp formats in event logs
            timestamp_formats = [
                "%Y-%m-%d %H:%M:%S",  # 2025-09-19 10:50:50
                "%Y-%m-%d-%H-%M-%S",  # 2025-12-16-08-55-17 (MCAP format)
                "%Y%m%d_%H%M%S",  # 20250919_093523
                "%Y-%m-%d_%H-%M-%S",  # 2025-09-19_09-35-23
                "%Y%m%d%H%M%S",  # 20250919093523
                "%H:%M:%S",  # 09:35:23 (time only)
                "%Y-%m-%d %H:%M:%S.%f",  # 2025-09-19 09:35:23.123456
                "%Y%m%d%H%M%S%f",  # 20250919093523123456 (with microseconds)
            ]

            # Try each format
            for fmt in timestamp_formats:
                try:
                    if fmt == "%H:%M:%S":
                        # For time-only format, assume today's date
                        from datetime import date

                        time_part = datetime.strptime(timestamp_str, fmt).time()
                        return datetime.combine(date.today(), time_part)
                    else:
                        return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue

            # If no format matches, log the actual timestamp format for debugging
            self.log_message(
                f"Unknown timestamp format: '{timestamp_str}' (length: {len(timestamp_str)})", is_error=True
            )
            return None

        except Exception as e:
            self.log_message(f"Error parsing timestamp '{timestamp_str}': {e}", is_error=True)
            return None

    def find_video_for_timestamp(self, event_log_path, event_time):
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
                video_start_time = self.parse_timestamp(timestamp_part)
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

    def find_mcap_for_timestamp(self, event_log_path, event_time):
        """Find the MCAP file that contains the specified timestamp."""
        try:
            # Extract date from event log path
            # Example: ~/data/20250919/TG-7737/PSA8600/logs -> ~/data/20250919/TG-7737/PSA8600/rosbags/default/...
            log_dir = os.path.dirname(event_log_path)
            base_dir = os.path.dirname(log_dir)  # Remove 'logs' part
            rosbags_dir = os.path.join(base_dir, "rosbags", "default")

            if not os.path.exists(rosbags_dir):
                self.log_message(f"Rosbags directory not found: {rosbags_dir}", is_error=True)
                return None, None

            # Find all MCAP files recursively in the rosbags/default directory
            # Structure: rosbags/default/timestamp_folder/timestamp.mcap
            mcap_files = []
            for root, dirs, files in os.walk(rosbags_dir):
                for file in files:
                    if file.endswith(".mcap"):
                        mcap_files.append(os.path.join(root, file))

            if not mcap_files:
                self.log_message(f"No MCAP files found in: {rosbags_dir}", is_error=True)
                return None, None

            # Parse MCAP filenames to find the one that contains our timestamp
            # MCAP format examples: 2025-09-19_09-35-23.mcap or similar
            best_mcap = None
            best_start_time = None

            for mcap_file in mcap_files:
                filename = os.path.basename(mcap_file)
                # Extract timestamp from filename (remove .mcap extension)
                timestamp_part = filename.replace(".mcap", "")

                # Parse MCAP start time
                mcap_start_time = self.parse_timestamp(timestamp_part)
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

    def play_bazel_at_timestamp(self, event_log_path, timestamp_str):
        """Play rosbag at the specified timestamp using Bazel Bag GUI."""
        try:
            # Parse the timestamp from the event log
            event_time = self.parse_timestamp(timestamp_str)
            if not event_time:
                self.log_message(f"Could not parse timestamp: {timestamp_str}", is_error=True)
                return

            # Find the corresponding MCAP file and offset
            mcap_file, start_offset = self.find_mcap_for_timestamp(event_log_path, event_time)
            if not mcap_file:
                self.log_message("No matching MCAP file found", is_error=True)
                return

            # Get settings from the logic's GUI manager (if available)
            try:
                # Try to get settings from parent GUI manager
                settings = getattr(self.logic, "settings", {})
                if not settings:
                    # Fallback to default settings
                    from ...core_logic import DEFAULT_SETTINGS

                    settings = DEFAULT_SETTINGS.copy()
            except (AttributeError, ImportError):
                # Fallback to default settings
                from ...core_logic import DEFAULT_SETTINGS

                settings = DEFAULT_SETTINGS.copy()

            # Launch bazel bag gui with the MCAP file and start time
            self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(mcap_file)} (closest to timestamp)...")
            message, error = self.logic.launch_bazel_bag_gui(mcap_file, settings, start_time=start_offset)

            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
            else:
                self.log_message(
                    f"Note: Bazel playback started at bag beginning. "
                    f"Use seek controls to navigate to ~{start_offset:.1f}s"
                )

        except Exception as e:
            self.log_message(f"Error playing bazel at timestamp: {e}", is_error=True)

    def navigate_to_mcap_from_timestamp(self, event_log_path, timestamp_str):
        """Navigate to the MCAP file in the file explorer based on the timestamp."""
        try:
            # Parse the timestamp from the event log
            event_time = self.parse_timestamp(timestamp_str)
            if not event_time:
                self.log_message(f"Could not parse timestamp: {timestamp_str}", is_error=True)
                return

            # Find the corresponding MCAP file
            mcap_file, start_offset = self.find_mcap_for_timestamp(event_log_path, event_time)
            if not mcap_file:
                self.log_message("No matching MCAP file found", is_error=True)
                return

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
