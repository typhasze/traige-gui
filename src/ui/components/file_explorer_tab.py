import os
import tkinter as tk
from tkinter import ttk, filedialog

class FileExplorerTab:
    def __init__(self, parent, root, logic, file_explorer_logic, log_message, update_button_states):
        self.frame = ttk.Frame(parent)
        self.root = root
        self.logic = logic
        self.file_explorer_logic = file_explorer_logic
        self.log_message = log_message
        self._update_button_states = update_button_states

        # State
        self._data_root = os.path.expanduser('~/data')
        self._abs_data_root = os.path.abspath(self._data_root)
        self.current_explorer_path = self._data_root
        self.explorer_history = []
        self._history_set = set()
        self.explorer_files_list = []

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
        self.explorer_path_entry = ttk.Entry(path_frame, textvariable=self.explorer_path_var)
        self.explorer_path_entry.pack(side=tk.LEFT, fill="x", expand=True)

        # Navigation buttons
        self.go_home_button = self._create_button(path_frame, "⌂", self.go_home_directory, side=tk.LEFT)
        self.go_back_button = self._create_button(path_frame, "⏎", self.go_back, side=tk.LEFT)

        # Search frame
        search_frame = ttk.Frame(self.frame)
        search_frame.pack(fill="x", padx=5, pady=5)

        search_label = ttk.Label(search_frame, text="Search Filter:")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.explorer_search_var = tk.StringVar()
        self.explorer_search_entry = ttk.Entry(search_frame, textvariable=self.explorer_search_var)
        self.explorer_search_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.clear_search_button = self._create_button(search_frame, "❌", self.clear_explorer_search, side=tk.LEFT)

        # Explorer listbox
        list_frame = ttk.Frame(self.frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.explorer_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, exportselection=False)
        self.explorer_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.explorer_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.explorer_listbox.config(yscrollcommand=scrollbar.set)

    def bind_events(self):
        self.explorer_path_entry.bind("<Return>", self.navigate_to_path)
        self.explorer_search_var.trace_add("write", self.on_explorer_search)
        self.explorer_search_entry.bind("<Return>", lambda e: self.explorer_listbox.focus_set())
        self.explorer_search_entry.bind("<Down>", self.focus_explorer_listbox_down)
        self.explorer_search_entry.bind("<Up>", self.focus_explorer_listbox_up)
        self.explorer_search_entry.bind("<Escape>", self.clear_explorer_search)
        self.explorer_listbox.bind("<<ListboxSelect>>", self.on_explorer_select)
        self.explorer_listbox.bind("<Double-1>", self.on_explorer_double_click)
        self.explorer_listbox.bind("<Return>", self.on_explorer_enter_key)
        self.explorer_listbox.bind("<BackSpace>", self.on_explorer_backspace_key)
        self.explorer_listbox.bind("<Key>", self.on_listbox_keypress)

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
        try:
            self.explorer_listbox.delete(0, tk.END)
            self.explorer_files_list = []
            
            if not os.path.isdir(self.current_explorer_path):
                self.log_message(f"Invalid directory: {self.current_explorer_path}", is_error=True)
                return
            
            self.explorer_path_var.set(self.current_explorer_path)
            
            dirs, files = self.file_explorer_logic.list_directory(self.current_explorer_path)
            
            search_text = self.explorer_search_var.get().strip()
            if search_text:
                search_lower = search_text.lower()
                dirs = [d for d in dirs if search_lower in d.lower()]
                files = [f for f in files if search_lower in f.lower()]
            
            batch_items = [(f"📁 {d}", d) for d in dirs]
            
            for f in files:
                item_path = os.path.join(self.current_explorer_path, f)
                info = self.file_explorer_logic.get_file_info(item_path)
                icon = info.get('icon', '')
                batch_items.append((f"{icon} {f}", f))
            
            for display_text, original_name in batch_items:
                self.explorer_listbox.insert(tk.END, display_text)
                self.explorer_files_list.append(original_name)
                
        except PermissionError:
            self.log_message(f"Permission denied: {self.current_explorer_path}", is_error=True)
        except Exception as e:
            self.log_message(f"Error refreshing explorer: {e}", is_error=True)

    def get_selected_explorer_mcap_paths(self):
        selection = self.explorer_listbox.curselection()
        if not selection:
            return []
        
        mcap_paths = []
        current_path = self.current_explorer_path
        files_list = self.explorer_files_list
        mcap_check = self.file_explorer_logic.is_mcap_file
        
        for idx in selection:
            if idx >= len(files_list): continue
            selected_item = files_list[idx]
            item_path = os.path.join(current_path, selected_item)
            if os.path.isfile(item_path) and mcap_check(item_path):
                mcap_paths.append(item_path)
        
        return mcap_paths

    def go_back(self):
        if self.explorer_history:
            # Pop from history and also from the set for consistency
            previous_path = self.explorer_history.pop()
            if previous_path in self._history_set:
                self._history_set.remove(previous_path)
            
            self.current_explorer_path = previous_path
            self.refresh_explorer()

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
        if current == self._abs_data_root: return
        parent_dir = os.path.dirname(current)
        if os.path.commonpath([parent_dir, self._abs_data_root]) != self._abs_data_root: return
        
        self._add_to_history(self.current_explorer_path)
        self.current_explorer_path = parent_dir
        self.refresh_explorer()

    def go_home_directory(self):
        """Navigate to the home directory, adding the current path to history if it's different."""
        # Add the current valid path to history if it's not the destination (home)
        if self.current_explorer_path != self._data_root:
            self._add_to_history(self.current_explorer_path)
        
        # Set the current path to home and refresh the view
        self.current_explorer_path = self._data_root
        self.refresh_explorer()

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
        success, msg = self.file_explorer_logic.open_file(file_path)
        if success:
            self.log_message(msg)
        else:
            self.log_message(msg, is_error=True)

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
        return 'break'

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
        return 'break'

    def focus_explorer_listbox_up(self, event=None):
        return self._focus_explorer_listbox_move(-1, event)

    def focus_explorer_listbox_down(self, event=None):
        return self._focus_explorer_listbox_move(1, event)
