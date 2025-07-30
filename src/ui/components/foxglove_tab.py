import os
import tkinter as tk
from tkinter import ttk, filedialog

class FoxgloveTab:
    def __init__(self, parent, root, logic, log_message, disable_file_specific_action_buttons, enable_file_specific_action_buttons):
        self.frame = ttk.Frame(parent)
        self.root = root
        self.logic = logic
        self.log_message = log_message
        self.disable_file_specific_action_buttons = disable_file_specific_action_buttons
        self.enable_file_specific_action_buttons = enable_file_specific_action_buttons

        # State
        self.current_mcap_folder_absolute = None
        self.mcap_filename_from_link = None
        self.mcap_files_list = []
        self._last_list_state = None

        # UI Widgets
        self.create_widgets()
        self.bind_events()

    def create_widgets(self):
        # Link analysis frame
        link_frame = ttk.Frame(self.frame)
        link_frame.pack(fill="x", padx=5, pady=5)
        
        link_label = ttk.Label(link_frame, text="Analyze Link:")
        link_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.link_var = tk.StringVar()
        self.link_entry = ttk.Entry(link_frame, textvariable=self.link_var)
        self.link_entry.pack(side=tk.LEFT, fill="x", expand=True)
        
        self.analyze_button = self._create_button(link_frame, "Analyze", self.analyze_link)
        self.clear_button = self._create_button(link_frame, "Clear", self.clear_link_and_list)

        # MCAP file list frame
        file_list_frame = ttk.Frame(self.frame)
        file_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.mcap_list_label = ttk.Label(file_list_frame, text="Files in: N/A")
        self.mcap_list_label.pack(fill="x")

        listbox_frame = ttk.Frame(file_list_frame)
        listbox_frame.pack(fill="both", expand=True)
        
        self.mcap_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED, exportselection=False)
        self.mcap_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.mcap_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.mcap_listbox.config(yscrollcommand=scrollbar.set)

    def bind_events(self):
        self.link_entry.bind("<Return>", lambda e: self.analyze_link())
        self.link_entry.bind("<Control-a>", self.select_all_text)
        self.link_entry.bind("<Control-A>", self.select_all_text)  # Handle Shift key
        self.mcap_listbox.bind("<<ListboxSelect>>", self.on_file_select)

    def select_all_text(self, event=None):
        """Select all text in the widget that triggered the event."""
        # The widget that generated the event is in event.widget
        if event and isinstance(event.widget, ttk.Entry):
            event.widget.select_range(0, tk.END)
            event.widget.icursor(tk.END)
        return "break"  # Prevents other bindings from firing

    def on_file_select(self, event=None, suppress_log=False):
        """Handle file selection in the listbox."""
        selection_indices = self.mcap_listbox.curselection()
        num_selected = len(selection_indices)
        
        if num_selected > 0:
            # Enable copy only for single selection
            copy_enabled = num_selected == 1
            # Enable Foxglove and Bazel for any MCAP selection (single or multiple)
            self.enable_file_specific_action_buttons(
                open_with_foxglove=True, 
                open_with_bazel=True, 
                copy_path=copy_enabled
            )
            if not suppress_log:
                self.log_message(f"{num_selected} file(s) selected.")
        else:
            self.disable_file_specific_action_buttons()

    def get_current_folder(self):
        """
        Returns the absolute path of the current folder being displayed.
        """
        return self.current_mcap_folder_absolute

    def get_selected_mcap_path(self):
        """Returns the full path for the first selected mcap file."""
        paths = self.get_selected_mcap_paths()
        return paths[0] if paths else None

    def get_selected_mcap_paths(self):
        """
        Returns a list of full paths for selected mcap files.
        Optimized with caching for better performance.
        """
        current_folder = self.get_current_folder()
        if not current_folder:
            return []
        
        selected_indices = self.mcap_listbox.curselection()
        if not selected_indices:
            return []
        
        # Batch process selections for better performance
        selected_paths = []
        for i in selected_indices:
            if i < len(self.mcap_files_list):  # Bounds check
                file_path = os.path.join(current_folder, self.mcap_files_list[i])
                selected_paths.append(file_path)
        
        return selected_paths

    def _create_button(self, parent, text, command, state=tk.NORMAL, **pack_opts):
        btn = ttk.Button(parent, text=text, command=command, state=state)
        btn.pack(side=tk.LEFT, padx=5, pady=5, **pack_opts)
        return btn

    def analyze_link(self):
        link = self.link_var.get()
        if not link:
            self.log_message("Please enter a link to analyze.", is_error=True)
            return

        extracted_remote_folder, self.mcap_filename_from_link = self.logic.extract_info_from_link(link)
        
        if not extracted_remote_folder:
            self.log_message("Could not extract information from link.", is_error=True)
            return

        self.log_message(f"Extracted remote folder: {extracted_remote_folder}")
        if self.mcap_filename_from_link:
            self.log_message(f"File from link: {self.mcap_filename_from_link}")

        self.current_mcap_folder_absolute = self.logic.get_local_folder_path(extracted_remote_folder)
        
        if not self.current_mcap_folder_absolute or not os.path.isdir(self.current_mcap_folder_absolute):
            self.log_message(f"Error: Local folder does not exist or could not be mapped: {self.current_mcap_folder_absolute}", is_error=True)
            self.clear_file_list_and_disable_buttons()
            return

        self.log_message(f"Mapped local folder: {self.current_mcap_folder_absolute}")
        
        display_folder_name = os.path.basename(self.current_mcap_folder_absolute)
        self.mcap_list_label.config(text=f"Files in: {display_folder_name} (Full path: {self.current_mcap_folder_absolute})")

        self.mcap_files_list, error = self.logic.list_files_in_directory(self.current_mcap_folder_absolute)
        if error:
            self.log_message(error, is_error=True)
        
        if not self.mcap_files_list:
            self.log_message("No files found in the directory.", is_error=False)

        self.populate_file_list()

    def clear_link_and_list(self):
        self.link_var.set("")
        self.mcap_filename_from_link = None
        self.current_mcap_folder_absolute = None # Reset folder context
        self.clear_file_list_and_disable_buttons()
        self.mcap_list_label.config(text="Files in: N/A")


    def clear_file_list_and_disable_buttons(self):
        self.mcap_listbox.delete(0, tk.END)
        self.mcap_files_list = []
        # Clear selection state properly
        self.mcap_listbox.selection_clear(0, tk.END)
        self.disable_file_specific_action_buttons()

    def populate_file_list(self):
        """
        Populate the file list with optimization for large directories.
        """
        current_state = (tuple(self.mcap_files_list), self.mcap_filename_from_link)
        
        # Skip population if state hasn't changed (optimization)
        if current_state == self._last_list_state:
            return
            
        # Clear existing items efficiently
        self.mcap_listbox.delete(0, tk.END)
        
        if not self.mcap_files_list:
            self._last_list_state = current_state
            return
        
        # Prepare target for highlighting with optimized comparison
        target = self.mcap_filename_from_link.strip().lower() if self.mcap_filename_from_link else None
        highlight_idx = -1
        
        # Pre-allocate list for better performance
        items_to_insert = []
        items_to_insert.reserve(len(self.mcap_files_list)) if hasattr(items_to_insert, 'reserve') else None
        
        # Single pass to prepare all items
        for i, filename in enumerate(self.mcap_files_list):
            is_target = target and filename.lower() == target
            items_to_insert.append((filename, is_target))
            if is_target:
                highlight_idx = i
        
        # Batch insert all items for better performance
        for i, (filename, is_target) in enumerate(items_to_insert):
            self.mcap_listbox.insert(tk.END, filename)
            if is_target:
                self.mcap_listbox.itemconfig(i, {'bg': 'yellow'})
            
        # Handle highlighting and selection efficiently
        if highlight_idx != -1:
            self.mcap_listbox.see(highlight_idx)
            self.mcap_listbox.selection_set(highlight_idx)
            # Trigger the selection handler to update button states properly
            self.on_file_select(suppress_log=True)
        else:
            self.disable_file_specific_action_buttons()
            
        # Cache the current state for future comparisons
        self._last_list_state = current_state
