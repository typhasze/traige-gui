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
        self.subfolder_tabs = None
        self.subfolder_tab_names = []
        self.subfolder_tab_paths = []
        self._last_list_state = None

        # UI Widgets
        self.create_widgets()
        self.bind_events()

        self.refresh_subfolder_tabs(base_path=None)

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

        # Subfolder tabs will be created here if needed by refresh_subfolder_tabs

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
            self.enable_file_specific_action_buttons(copy_path=copy_enabled)
            if not suppress_log:
                self.log_message(f"{num_selected} file(s) selected.")
        else:
            self.disable_file_specific_action_buttons()

    def get_current_folder(self):
        """
        Returns the absolute path of the current folder being displayed.
        If subfolder tabs are active, it returns the path of the selected subfolder tab.
        Otherwise, it returns the path of the folder from the analyzed link.
        """
        if hasattr(self, 'subfolder_tabs') and self.subfolder_tabs and self.subfolder_tabs.winfo_exists():
            try:
                selected_tab_index = self.subfolder_tabs.index(self.subfolder_tabs.select())
                if selected_tab_index < len(self.subfolder_tab_paths):
                    return self.subfolder_tab_paths[selected_tab_index]
            except tk.TclError:
                # This can happen if no tab is selected.
                pass
        
        return self.current_mcap_folder_absolute

    def get_selected_mcap_path(self):
        """Returns the full path for the first selected mcap file."""
        paths = self.get_selected_mcap_paths()
        return paths[0] if paths else None

    def get_selected_mcap_paths(self):
        """Returns a list of full paths for selected mcap files."""
        current_folder = self.get_current_folder()
        if not current_folder:
            return []
        
        selected_indices = self.mcap_listbox.curselection()
        return [os.path.join(current_folder, self.mcap_listbox.get(i)) for i in selected_indices]

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
        
        if not extracted_remote_folder or not self.mcap_filename_from_link:
            self.log_message("Could not extract information from link.", is_error=True)
            return

        self.log_message(f"Extracted remote folder: {extracted_remote_folder}")
        self.log_message(f"MCAP file from link: {self.mcap_filename_from_link}")

        self.current_mcap_folder_absolute = self.logic.get_local_folder_path(extracted_remote_folder)
        
        if not self.current_mcap_folder_absolute or not os.path.isdir(self.current_mcap_folder_absolute):
            self.log_message(f"Error: Local folder does not exist or could not be mapped: {self.current_mcap_folder_absolute}", is_error=True)
            self.clear_file_list_and_disable_buttons()
            return

        self.log_message(f"Mapped local folder: {self.current_mcap_folder_absolute}")
        
        display_folder_name = os.path.basename(self.current_mcap_folder_absolute)
        self.mcap_list_label.config(text=f"Files in: {display_folder_name} (Full path: {self.current_mcap_folder_absolute})")

        self.mcap_files_list, error = self.logic.list_mcap_files(self.current_mcap_folder_absolute)
        if error:
            self.log_message(error, is_error=True)
        
        if not self.mcap_files_list:
            self.log_message("No .mcap files found in the directory.", is_error=False)

        self.populate_file_list()

        resolved_folder = self.current_mcap_folder_absolute
        if resolved_folder:
            self.refresh_subfolder_tabs(base_path=resolved_folder)

    def clear_link_and_list(self):
        self.link_var.set("")
        self.mcap_filename_from_link = None
        self.current_mcap_folder_absolute = None # Reset folder context
        self.clear_file_list_and_disable_buttons()
        self.mcap_list_label.config(text="Files in: N/A")


    def clear_file_list_and_disable_buttons(self):
        self.mcap_listbox.delete(0, tk.END)
        self.mcap_files_list = []
        self.disable_file_specific_action_buttons()

    def populate_file_list(self):
        current_state = (tuple(self.mcap_files_list), self.mcap_filename_from_link)
        if current_state == self._last_list_state:
            return
            
        self.mcap_listbox.delete(0, tk.END)
        highlight_idx = -1
        target = self.mcap_filename_from_link.strip().lower() if self.mcap_filename_from_link else None
        
        batch_items = []
        for i, filename in enumerate(self.mcap_files_list):
            is_target = target and filename.lower() == target
            batch_items.append((filename, is_target))
            if is_target:
                highlight_idx = i
        
        for i, (filename, is_target) in enumerate(batch_items):
            self.mcap_listbox.insert(tk.END, filename)
            if is_target:
                self.mcap_listbox.itemconfig(i, {'bg': 'yellow'})
            
        if highlight_idx != -1:
            self.mcap_listbox.see(highlight_idx)
            self.mcap_listbox.selection_set(highlight_idx)
            self.enable_file_specific_action_buttons()
        else:
            self.disable_file_specific_action_buttons()

        # Refresh subfolder tabs after populating the file list
        # self.refresh_subfolder_tabs() # This is now called from analyze_link and on_subfolder_tab_changed

    def refresh_subfolder_tabs(self, base_path):
        """Create or update subfolder tabs based on the given base path."""
        # Destroy existing notebook if it exists to prevent stacking them
        if hasattr(self, 'subfolder_tabs') and self.subfolder_tabs:
            self.subfolder_tabs.destroy()
            self.subfolder_tabs = None
            self.subfolder_tab_names = []
            self.subfolder_tab_paths = []

        if not base_path or not os.path.isdir(base_path):
            # Also destroy tabs if the base path becomes invalid
            if hasattr(self, 'subfolder_tabs') and self.subfolder_tabs:
                self.subfolder_tabs.destroy()
            return

        subfolders = sorted([d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))])

        if not subfolders:
            # Destroy tabs if there are no subfolders to show
            if hasattr(self, 'subfolder_tabs') and self.subfolder_tabs:
                self.subfolder_tabs.destroy()
            return

        # Create a new notebook for subfolder tabs
        self.subfolder_tabs = ttk.Notebook(self.frame)
        self.subfolder_tabs.pack(fill="x", padx=5, pady=(5, 0))

        for folder in subfolders:
            folder_path = os.path.join(base_path, folder)
            tab_frame = ttk.Frame(self.subfolder_tabs)
            self.subfolder_tabs.add(tab_frame, text=folder)
            
            # Store paths for later use
            self.subfolder_tab_names.append(folder)
            self.subfolder_tab_paths.append(folder_path)

            # You can add content to tab_frame here if needed, e.g., a label
            # label = ttk.Label(tab_frame, text=f"Contents of {folder}")
            # label.pack(padx=5, pady=5)

        self.subfolder_tabs.bind("<<NotebookTabChanged>>", self.on_subfolder_tab_changed)

    def on_subfolder_tab_changed(self, event):
        """Handle switching between subfolder tabs."""
        if not self.subfolder_tabs:
            return
            
        selected_tab_index = self.subfolder_tabs.index(self.subfolder_tabs.select())
        new_path = self.subfolder_tab_paths[selected_tab_index]

        self.current_mcap_folder_absolute = new_path
        
        display_folder_name = os.path.basename(self.current_mcap_folder_absolute)
        self.mcap_list_label.config(text=f"Files in: {display_folder_name} (Full path: {self.current_mcap_folder_absolute})")

        self.mcap_files_list, error = self.logic.list_mcap_files(self.current_mcap_folder_absolute)
        if error:
            self.log_message(error, is_error=True)
        
        if not self.mcap_files_list:
            self.log_message("No .mcap files found in this sub-directory.", is_error=False)

        self.populate_file_list()
        # Refresh the sub-sub-folders
        self.refresh_subfolder_tabs(base_path=new_path)
