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

        self.refresh_subfolder_tabs()

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
        self.mcap_listbox.bind("<<ListboxSelect>>", self.on_file_select)

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
        self.log_message(f"Mapped local folder: {self.current_mcap_folder_absolute}")
        
        display_folder_name = os.path.basename(self.current_mcap_folder_absolute) if self.current_mcap_folder_absolute else "N/A"
        self.mcap_list_label.config(text=f"Files in: {display_folder_name} (Full path: {self.current_mcap_folder_absolute})")

        self.mcap_files_list, error = self.logic.list_mcap_files(self.current_mcap_folder_absolute)
        if error:
            self.log_message(error, is_error=True)
        
        if not self.mcap_files_list:
            self.log_message("No .mcap files found in the directory.", is_error=True)

        self.populate_file_list()

        resolved_folder = self.current_mcap_folder_absolute
        if resolved_folder:
            self.refresh_subfolder_tabs(default_folder=resolved_folder)

    def clear_link_and_list(self):
        self.link_var.set("")
        self.mcap_filename_from_link = None
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
            
        self._last_list_state = current_state

    def on_file_select(self, event=None, suppress_log=False):
        if self.mcap_listbox.curselection():
            self.enable_file_specific_action_buttons()
        else:
            self.disable_file_specific_action_buttons()

    def get_selected_mcap_path(self):
        selection_indices = self.mcap_listbox.curselection()
        if not selection_indices:
            return None
        selected_filename = self.mcap_listbox.get(selection_indices[0])
        if self.current_mcap_folder_absolute and os.path.isdir(self.current_mcap_folder_absolute):
             return os.path.join(self.current_mcap_folder_absolute, selected_filename)
        self.log_message("Error: Current MCAP folder path is not set or invalid.", is_error=True)
        return None

    def get_selected_mcap_paths(self):
        selection_indices = self.mcap_listbox.curselection()
        selected_paths = []
        for idx in selection_indices:
            selected_filename = self.mcap_listbox.get(idx)
            if self.current_mcap_folder_absolute and os.path.isdir(self.current_mcap_folder_absolute):
                selected_paths.append(os.path.join(self.current_mcap_folder_absolute, selected_filename))
        return selected_paths

    def on_subfolder_tab_changed(self, event):
        if not self.subfolder_tabs: return
        idx = self.subfolder_tabs.index(self.subfolder_tabs.select())
        new_folder = self.subfolder_tab_paths[idx]
        
        if new_folder == self.current_mcap_folder_absolute: return
            
        self.current_mcap_folder_absolute = new_folder
        display_folder_name = self.subfolder_tab_names[idx]
        
        self.mcap_list_label.config(text=f"Files in: {display_folder_name} (Full path: {new_folder})")
        
        self.mcap_files_list, error = self.logic.list_mcap_files(new_folder)
        if error:
            self.log_message(error, is_error=True)
            self.clear_file_list_and_disable_buttons()
            return
            
        if not self.mcap_files_list:
            self.log_message("No .mcap files found in the directory.", is_error=True)
            self.clear_file_list_and_disable_buttons()
            return
            
        self.populate_file_list()

    def browse_default_folder(self):
        folder = filedialog.askdirectory(title="Select 'default' folder")
        if folder:
            self.refresh_subfolder_tabs(default_folder=folder)

    def refresh_subfolder_tabs(self, default_folder=None):
        if self.subfolder_tabs:
            self.subfolder_tabs.destroy()
            self.subfolder_tabs = None
            self.subfolder_tab_names = []
            self.subfolder_tab_paths = []

        if default_folder is None:
            current_path = self.current_mcap_folder_absolute or os.path.expanduser('~/data/default')
            default_folder = self.logic.get_effective_default_folder(current_path)

        subfolders = self.logic.list_subfolders_in_path(default_folder)
        file_list_frame = self.mcap_list_label.master

        if len(subfolders) > 1:
            self.subfolder_tabs = ttk.Notebook(file_list_frame)
            for folder in subfolders:
                tab_name = os.path.basename(folder)
                self.subfolder_tab_names.append(tab_name)
                self.subfolder_tab_paths.append(folder)
                tab_frame = ttk.Frame(self.subfolder_tabs)
                self.subfolder_tabs.add(tab_frame, text=tab_name)
            self.subfolder_tabs.pack(fill="x", pady=(0, 5))
            self.subfolder_tabs.bind("<<NotebookTabChanged>>", self.on_subfolder_tab_changed)
            self.current_mcap_folder_absolute = self.subfolder_tab_paths[0]
        elif len(subfolders) == 1:
            self.current_mcap_folder_absolute = subfolders[0]
        else:
            self.current_mcap_folder_absolute = None

        if self.subfolder_tabs:
            self.on_subfolder_tab_changed(None)
        elif self.current_mcap_folder_absolute:
            display_folder_name = os.path.basename(self.current_mcap_folder_absolute)
            self.mcap_list_label.config(text=f"Files in: {display_folder_name} (Full path: {self.current_mcap_folder_absolute})")
            self.mcap_files_list, error = self.logic.list_mcap_files(self.current_mcap_folder_absolute)
            if not error and self.mcap_files_list:
                self.populate_file_list()
            else:
                self.clear_file_list_and_disable_buttons()
        else:
            self.clear_file_list_and_disable_buttons()
