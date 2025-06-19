import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Listbox, Scrollbar, Frame, Label, Entry, Button, Text, END, SINGLE, VERTICAL, HORIZONTAL
import os
import signal
from core_logic import FoxgloveLogic # Assuming core_logic.py is in the same directory
import shutil

class FoxgloveAppGUIManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Foxglove MCAP Launcher")
        self.logic = FoxgloveLogic()
        
        self.current_mcap_folder_absolute = None
        self.mcap_filename_from_link = None
        self.mcap_files_list = []

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_signal_handlers()
        # Set a minimum size for the window
        self.root.minsize(700, 550)


    def log_message(self, message, is_error=False, clear_first=False):
        self.status_text.config(state=tk.NORMAL)
        if clear_first:
            self.status_text.delete('1.0', tk.END)
        
        tag = "error" if is_error else "info"
        prefix = "ERROR: " if is_error else "INFO: "
        
        # Split message by newlines to apply tags correctly if needed
        for line in message.splitlines():
            self.status_text.insert(tk.END, f"{prefix}{line}\n", tag)
            
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(main_frame, text="Foxglove Link Analysis", padding="10")
        input_frame.pack(padx=5, pady=5, fill="x")

        Label(input_frame, text="Foxglove Link:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.link_entry = ttk.Entry(input_frame, width=60)
        self.link_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.analyze_button = ttk.Button(input_frame, text="Analyze Link", command=self.analyze_link)
        self.analyze_button.grid(row=0, column=2, padx=5, pady=5)
        input_frame.columnconfigure(1, weight=1)

        # --- File List Frame ---
        file_list_frame = ttk.LabelFrame(main_frame, text="MCAP Files", padding="10")
        file_list_frame.pack(padx=5, pady=5, fill="both", expand=True)

        # Tabs for subfolders in default
        self.subfolder_tabs = None
        self.subfolder_tab_names = []
        self.subfolder_tab_paths = []
        subfolders = self.logic.list_default_subfolders()
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

        self.mcap_list_label = ttk.Label(file_list_frame, text="Files in folder:")
        self.mcap_list_label.pack(anchor="w", pady=(0,5))

        list_container = ttk.Frame(file_list_frame)
        list_container.pack(fill="both", expand=True)

        yscrollbar = Scrollbar(list_container, orient=VERTICAL)
        xscrollbar = Scrollbar(list_container, orient=HORIZONTAL)
        
        self.mcap_listbox = Listbox(list_container, selectmode=tk.EXTENDED, 
                                    yscrollcommand=yscrollbar.set, xscrollcommand=xscrollbar.set,
                                    height=10, exportselection=False) # exportselection=False is important
        
        yscrollbar.config(command=self.mcap_listbox.yview)
        xscrollbar.config(command=self.mcap_listbox.xview)
        
        yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        xscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.mcap_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        self.mcap_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        # --- Action Buttons Frame ---
        action_frame = ttk.LabelFrame(main_frame, text="Launch Actions", padding="10")
        action_frame.pack(padx=5, pady=5, fill="x")

        self.launch_foxglove_button = ttk.Button(action_frame, text="Open with Foxglove", command=self.launch_foxglove_selected, state=tk.DISABLED)
        self.launch_foxglove_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.launch_bazel_gui_button = ttk.Button(action_frame, text="Open with Bazel Bag GUI", command=self.launch_bazel_gui_selected, state=tk.DISABLED)
        self.launch_bazel_gui_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")
        
        self.launch_bazel_viz_button = ttk.Button(action_frame, text="Launch Bazel Tools Viz", command=self.launch_bazel_viz) # No file needed
        self.launch_bazel_viz_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.launch_all_button = ttk.Button(action_frame, text="Launch All for Selected", command=self.launch_all_selected, state=tk.DISABLED)
        self.launch_all_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")


        # --- Status/Log Frame ---
        status_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        status_frame.pack(padx=5, pady=5, fill="both", expand=True)
        
        log_container = ttk.Frame(status_frame)
        log_container.pack(fill="both", expand=True)

        log_yscrollbar = Scrollbar(log_container, orient=VERTICAL)
        self.status_text = Text(log_container, height=6, wrap=tk.WORD, yscrollcommand=log_yscrollbar.set, state=tk.DISABLED)
        log_yscrollbar.config(command=self.status_text.yview)
        log_yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.pack(side=tk.LEFT, fill="both", expand=True)
        
        self.status_text.tag_configure("error", foreground="red")
        self.status_text.tag_configure("info", foreground="black")


        # --- Default Folder Selection ---
        folder_select_frame = ttk.Frame(main_frame)
        folder_select_frame.pack(padx=5, pady=(0,5), fill="x")
        ttk.Label(folder_select_frame, text="Default folder path:").pack(side=tk.LEFT)
        self.default_folder_var = tk.StringVar()
        self.default_folder_entry = ttk.Entry(folder_select_frame, textvariable=self.default_folder_var, width=60)
        self.default_folder_entry.pack(side=tk.LEFT, padx=5, fill="x", expand=True)
        self.default_folder_browse = ttk.Button(folder_select_frame, text="Browse", command=self.browse_default_folder)
        self.default_folder_browse.pack(side=tk.LEFT, padx=5)
        # Set initial value (optional: could use last used or a guess)
        self.default_folder_var.set(os.path.expanduser('~/data/default'))

        # After widget creation, load tabs for the initial default folder
        self.refresh_subfolder_tabs()

    def analyze_link(self):
        link = self.link_entry.get()
        if not link:
            self.log_message("Please enter a Foxglove link.", is_error=True, clear_first=True)
            return

        self.log_message(f"Analyzing link: {link}", clear_first=True)
        extracted_remote_folder, self.mcap_filename_from_link = self.logic.extract_mcap_details_from_foxglove_link(link)

        if not extracted_remote_folder or not self.mcap_filename_from_link:
            self.log_message("Could not extract MCAP details from the link.", is_error=True)
            self.clear_file_list_and_disable_buttons()
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
            self.clear_file_list_and_disable_buttons()
            return
        
        if not self.mcap_files_list:
            self.log_message("No .mcap files found in the directory.", is_error=True) # Changed to error
            self.clear_file_list_and_disable_buttons()
            return

        self.populate_file_list()

        # --- Update default folder and tabs for link search ---
        # Find the parent 'default' folder of the resolved folder
        resolved_folder = self.current_mcap_folder_absolute
        if resolved_folder:
            parent_default = resolved_folder
            while parent_default and os.path.basename(parent_default) != 'default':
                parent_default = os.path.dirname(parent_default)
            if os.path.basename(parent_default) == 'default':
                self.default_folder_var.set(parent_default)
                self.refresh_subfolder_tabs()
                # Try to select the correct tab
                if self.subfolder_tabs and resolved_folder in self.subfolder_tab_paths:
                    idx = self.subfolder_tab_paths.index(resolved_folder)
                    self.subfolder_tabs.select(idx)

    def clear_file_list_and_disable_buttons(self):
        self.mcap_listbox.delete(0, tk.END)
        self.mcap_files_list = []
        # self.current_mcap_folder_absolute = None # Keep for label
        # self.mcap_filename_from_link = None # Keep for context
        self.disable_file_specific_action_buttons()


    def populate_file_list(self):
        self.mcap_listbox.delete(0, tk.END)
        highlight_idx = -1
        for i, filename in enumerate(self.mcap_files_list):
            self.mcap_listbox.insert(tk.END, filename)
            if filename == self.mcap_filename_from_link:
                self.mcap_listbox.itemconfig(i, {'bg':'#FFFF99'}) # Light yellow
                highlight_idx = i
        
        if highlight_idx != -1:
            self.mcap_listbox.selection_set(highlight_idx)
            self.mcap_listbox.see(highlight_idx)
            self.on_file_select(None) 
        else:
            self.log_message(f"Note: File from link ('{self.mcap_filename_from_link}') not found in the listed files.")
            self.disable_file_specific_action_buttons()


    def on_file_select(self, event): # event can be None
        selection = self.mcap_listbox.curselection()
        if selection:
            self.enable_file_specific_action_buttons()
            self.log_message(f"Selected {len(selection)} bag(s).", clear_first=False)
        else:
            self.disable_file_specific_action_buttons()

    def enable_file_specific_action_buttons(self):
        self.launch_foxglove_button.config(state=tk.NORMAL)
        self.launch_bazel_gui_button.config(state=tk.NORMAL)
        self.launch_all_button.config(state=tk.NORMAL)

    def disable_file_specific_action_buttons(self):
        self.launch_foxglove_button.config(state=tk.DISABLED)
        self.launch_bazel_gui_button.config(state=tk.DISABLED)
        self.launch_all_button.config(state=tk.DISABLED)

    def get_selected_mcap_path(self):
        selection_indices = self.mcap_listbox.curselection()
        if not selection_indices:
            self.log_message("No MCAP file selected.", is_error=True)
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

    def launch_foxglove_selected(self):
        selected_paths = self.get_selected_mcap_paths()
        if not selected_paths:
            self.log_message("No MCAP file selected.", is_error=True)
            return
        last_path = selected_paths[-1]
        self.log_message(f"Launching Foxglove with {os.path.basename(last_path)}...")
        message, error = self.logic.launch_foxglove(last_path)
        if message: self.log_message(message)
        if error: self.log_message(error, is_error=True)

    def launch_bazel_gui_selected(self):
        selected_paths = self.get_selected_mcap_paths()
        if not selected_paths:
            self.log_message("No MCAP file(s) selected.", is_error=True)
            return
        if len(selected_paths) == 1:
            self.log_message(f"Launching Bazel Bag GUI for {os.path.basename(selected_paths[0])}...")
            message, error = self.logic.launch_bazel_bag_gui(selected_paths[0])
            if message: self.log_message(message)
            if error: self.log_message(error, is_error=True)
        else:
            self.log_message(f"Launching Bazel Bag GUI for {len(selected_paths)} selected bags using symlinks...")
            message, error, symlink_dir = self.logic.play_bazel_bag_gui_with_symlinks(selected_paths)
            if message: self.log_message(message)
            if error: self.log_message(error, is_error=True)
            # No cleanup of symlink_dir as per new requirement

    def launch_bazel_viz(self):
        self.log_message(f"Launching Bazel Tools Viz...")
        message, error = self.logic.launch_bazel_tools_viz()
        if message: self.log_message(message)
        if error: self.log_message(error, is_error=True)
            
    def launch_all_selected(self):
        selected_path = self.get_selected_mcap_path()
        if selected_path:
            self.log_message(f"Launching all tools for {os.path.basename(selected_path)}...")
            
            msg_fox, err_fox = self.logic.launch_foxglove(selected_path)
            if msg_fox: self.log_message(f"Foxglove: {msg_fox}")
            if err_fox: self.log_message(f"Foxglove: {err_fox}", is_error=True)

            msg_gui, err_gui = self.logic.launch_bazel_bag_gui(selected_path)
            if msg_gui: self.log_message(f"Bazel Bag GUI: {msg_gui}")
            if err_gui: self.log_message(f"Bazel Bag GUI: {err_gui}", is_error=True)
            
            # Bazel Tools Viz is launched without a file argument here
            msg_viz, err_viz = self.logic.launch_bazel_tools_viz()
            if msg_viz: self.log_message(f"Bazel Tools Viz: {msg_viz}")
            if err_viz: self.log_message(f"Bazel Tools Viz: {err_viz}", is_error=True)

    def on_closing(self):
        # Clean up symlink dir if it exists
        symlink_dir = '/tmp/selected_bags_symlinks'
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
        import sys
        def handler(signum, frame):
            self.on_closing()
            sys.exit(0)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def on_subfolder_tab_changed(self, event):
        if self.subfolder_tabs:
            idx = self.subfolder_tabs.index(self.subfolder_tabs.select())
            self.current_mcap_folder_absolute = self.subfolder_tab_paths[idx]
            display_folder_name = self.subfolder_tab_names[idx]
            self.mcap_list_label.config(text=f"Files in: {display_folder_name} (Full path: {self.current_mcap_folder_absolute})")
            self.mcap_files_list, error = self.logic.list_mcap_files(self.current_mcap_folder_absolute)
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
            self.default_folder_var.set(folder)
            self.refresh_subfolder_tabs()

    def refresh_subfolder_tabs(self):
        # Remove old tabs if any
        if self.subfolder_tabs:
            self.subfolder_tabs.destroy()
            self.subfolder_tabs = None
            self.subfolder_tab_names = []
            self.subfolder_tab_paths = []
        default_folder = self.default_folder_var.get()
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
        # Update file list for the selected tab/folder
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