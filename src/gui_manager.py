import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Listbox, Scrollbar, Frame, Label, Entry, Button, Text, END, SINGLE, VERTICAL, HORIZONTAL
import os
import signal
import subprocess
import platform
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
        
        # File explorer variables
        self.current_explorer_path = os.path.expanduser("~/data")
        self.explorer_files_list = []
        self.explorer_view_mode = tk.StringVar(value="detailed")  # detailed, simple, icons
        self.explorer_history = []  # Navigation history

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_signal_handlers()
        # Set a minimum size for the window
        self.root.minsize(800, 600)


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

        # Create main tab system
        self.main_notebook = ttk.Notebook(main_frame)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)

        # Create Foxglove tab
        self.foxglove_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.foxglove_frame, text="Foxglove MCAP")
        
        # Create File Explorer tab
        self.explorer_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.explorer_frame, text="File Explorer")

        # Create widgets for each tab
        self.create_foxglove_widgets()
        self.create_explorer_widgets()
        
        # Set up logging frame that's shared between tabs
        self.create_shared_log_frame(main_frame)

    def create_foxglove_widgets(self):
        # --- Input Frame ---
        input_frame = ttk.LabelFrame(self.foxglove_frame, text="Foxglove Link Analysis", padding="10")
        input_frame.pack(padx=5, pady=5, fill="x")

        Label(input_frame, text="Foxglove Link:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.link_entry = ttk.Entry(input_frame, width=60)
        self.link_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # Enable Ctrl+A to select all text in the entry (Linux/Windows/Mac)
        def select_all(event):
            event.widget.focus_set()
            event.widget.select_range(0, 'end')
            return 'break'
        self.link_entry.bind('<Control-a>', select_all)
        self.link_entry.bind('<Control-A>', select_all)
        self.analyze_button = ttk.Button(input_frame, text="Analyze Link", command=self.analyze_link)
        self.analyze_button.grid(row=0, column=2, padx=5, pady=5)
        input_frame.columnconfigure(1, weight=1)

        # --- File List Frame ---
        file_list_frame = ttk.LabelFrame(self.foxglove_frame, text="MCAP Files", padding="10")
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
        action_frame = ttk.LabelFrame(self.foxglove_frame, text="Launch Actions", padding="10")
        action_frame.pack(padx=5, pady=5, fill="x")

        self.launch_foxglove_button = ttk.Button(action_frame, text="Open with Foxglove", command=self.launch_foxglove_selected, state=tk.DISABLED)
        self.launch_foxglove_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        # New button: Open Foxglove with Browser (does nothing for now)
        self.launch_foxglove_browser_button = ttk.Button(action_frame, text="Open Foxglove with Browser", command=self.open_foxglove_with_browser, state=tk.NORMAL)
        self.launch_foxglove_browser_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.launch_bazel_gui_button = ttk.Button(action_frame, text="Open with Bazel Bag GUI", command=self.launch_bazel_gui_selected, state=tk.DISABLED)
        self.launch_bazel_gui_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")
        
        self.launch_bazel_viz_button = ttk.Button(action_frame, text="Launch Bazel Tools Viz", command=self.launch_bazel_viz) # No file needed
        self.launch_bazel_viz_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.launch_all_button = ttk.Button(action_frame, text="Launch All for Selected", command=self.launch_all_selected, state=tk.DISABLED)
        self.launch_all_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        # --- Current Folder Selection ---
        folder_select_frame = ttk.Frame(self.foxglove_frame)
        folder_select_frame.pack(padx=5, pady=(0,5), fill="x")
        ttk.Label(folder_select_frame, text="Current folder path:").pack(side=tk.LEFT)
        self.current_subfolder_var = tk.StringVar()
        self.current_subfolder_entry = ttk.Entry(folder_select_frame, textvariable=self.current_subfolder_var, width=60, state="readonly")
        self.current_subfolder_entry.pack(side=tk.LEFT, padx=5, fill="x", expand=True)
        # Enable Ctrl+A to select all text in the current subfolder path entry (read-only, for copying)
        def select_all(event):
            event.widget.focus_set()
            event.widget.select_range(0, 'end')
            return 'break'
        self.current_subfolder_entry.bind('<Control-a>', select_all)
        self.current_subfolder_entry.bind('<Control-A>', select_all)
        self.current_subfolder_var.set("")

        # After widget creation, load tabs for the initial default folder
        self.refresh_subfolder_tabs()

    def create_explorer_widgets(self):
        # --- Path Navigation Frame ---
        nav_frame = ttk.Frame(self.explorer_frame)
        nav_frame.pack(fill="x", padx=5, pady=5)
        
        # Navigation buttons
        nav_buttons_frame = ttk.Frame(nav_frame)
        nav_buttons_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Button(nav_buttons_frame, text="⬅️ Back", command=self.go_back).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(nav_buttons_frame, text="⬆️ Up", command=self.go_up_directory).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(nav_buttons_frame, text="💾 Data", command=self.go_home_directory).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(nav_buttons_frame, text="📁 Browse", command=self.browse_directory).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(nav_buttons_frame, text="🔄 Refresh", command=self.refresh_explorer).pack(side=tk.LEFT, padx=(0,5))
        
        # View options
        view_frame = ttk.LabelFrame(nav_buttons_frame, text="View", padding="5")
        view_frame.pack(side=tk.RIGHT, padx=(5,0))
        
        ttk.Radiobutton(view_frame, text="📋 Detailed", variable=self.explorer_view_mode, 
                       value="detailed", command=self.refresh_explorer).pack(side=tk.LEFT)
        ttk.Radiobutton(view_frame, text="📄 Simple", variable=self.explorer_view_mode, 
                       value="simple", command=self.refresh_explorer).pack(side=tk.LEFT)
        ttk.Radiobutton(view_frame, text="🗂️ Icons", variable=self.explorer_view_mode, 
                       value="icons", command=self.refresh_explorer).pack(side=tk.LEFT)
        
        # Current path display
        path_frame = ttk.Frame(nav_frame)
        path_frame.pack(fill="x")
        ttk.Label(path_frame, text="Path:").pack(side=tk.LEFT, padx=(0,5))
        self.explorer_path_var = tk.StringVar(value=self.current_explorer_path)
        self.explorer_path_entry = ttk.Entry(path_frame, textvariable=self.explorer_path_var, width=50)
        self.explorer_path_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0,5))
        self.explorer_path_entry.bind('<Return>', self.navigate_to_path)
        
        ttk.Button(path_frame, text="Go", command=self.navigate_to_path).pack(side=tk.LEFT)

        # --- Search/Filter Bar ---
        search_frame = ttk.Frame(self.explorer_frame)
        search_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.explorer_search_var = tk.StringVar()
        self.explorer_search_entry = ttk.Entry(search_frame, textvariable=self.explorer_search_var, width=30)
        self.explorer_search_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.explorer_search_entry.bind('<KeyRelease>', self.on_explorer_search)
        self.explorer_search_entry.bind('<Down>', self.focus_explorer_listbox)
        self.explorer_search_entry.bind('<Up>', self.focus_explorer_listbox)
        self.explorer_search_entry.bind('<Return>', self.select_first_and_focus_listbox)
        self.explorer_search_entry.bind('<Escape>', self.clear_search_and_focus)
        clear_btn = ttk.Button(search_frame, text="Clear", command=self.clear_explorer_search)
        clear_btn.pack(side=tk.LEFT, padx=(5, 0))

        # --- File/Folder List Frame ---
        explorer_list_frame = ttk.LabelFrame(self.explorer_frame, text="Files and Folders", padding="10")
        explorer_list_frame.pack(padx=5, pady=5, fill="both", expand=True)

        # Create listbox with scrollbars
        explorer_container = ttk.Frame(explorer_list_frame)
        explorer_container.pack(fill="both", expand=True)

        explorer_yscrollbar = Scrollbar(explorer_container, orient=VERTICAL)
        explorer_xscrollbar = Scrollbar(explorer_container, orient=HORIZONTAL)
        
        self.explorer_listbox = Listbox(explorer_container, selectmode=tk.EXTENDED,
                                      yscrollcommand=explorer_yscrollbar.set, 
                                      xscrollcommand=explorer_xscrollbar.set,
                                      height=15, exportselection=False)
        
        explorer_yscrollbar.config(command=self.explorer_listbox.yview)
        explorer_xscrollbar.config(command=self.explorer_listbox.xview)
        
        explorer_yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        explorer_xscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.explorer_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        self.explorer_listbox.bind('<Double-Button-1>', self.on_explorer_double_click)
        self.explorer_listbox.bind('<<ListboxSelect>>', self.on_explorer_select)
        self.explorer_listbox.bind('<Return>', self.on_explorer_listbox_enter)
        self.explorer_listbox.bind('<Escape>', self.clear_search_and_focus)
        self.explorer_listbox.bind('<BackSpace>', self.on_explorer_listbox_backspace)

        # --- File Actions Frame ---
        file_actions_frame = ttk.LabelFrame(self.explorer_frame, text="File Actions", padding="10")
        file_actions_frame.pack(padx=5, pady=5, fill="x")

        self.open_file_button = ttk.Button(file_actions_frame, text="Open File", command=self.open_selected_file, state=tk.DISABLED)
        self.open_file_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.open_with_foxglove_button = ttk.Button(file_actions_frame, text="Open with Foxglove", command=self.open_with_foxglove, state=tk.DISABLED)
        self.open_with_foxglove_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.open_with_bazel_button = ttk.Button(file_actions_frame, text="Open with Bazel", command=self.open_with_bazel, state=tk.DISABLED)
        self.open_with_bazel_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.open_multiple_bazel_button = ttk.Button(file_actions_frame, text="Open Multiple with Bazel", command=self.open_multiple_with_bazel, state=tk.DISABLED)
        self.open_multiple_bazel_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.open_folder_button = ttk.Button(file_actions_frame, text="Open in File Manager", command=self.open_in_file_manager)
        self.open_folder_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.copy_path_button = ttk.Button(file_actions_frame, text="Copy Path", command=self.copy_selected_path, state=tk.DISABLED)
        self.copy_path_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        # Load initial directory
        self.refresh_explorer()

    def create_shared_log_frame(self, parent_frame):
        # --- Status/Log Frame ---
        status_frame = ttk.LabelFrame(parent_frame, text="Log", padding="10")
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
            self.log_message("No .mcap files found in the directory.", is_error=True)
            self.clear_file_list_and_disable_buttons()
            return

        self.populate_file_list()

        # --- Update default folder and tabs for link search ---
        resolved_folder = self.current_mcap_folder_absolute
        if resolved_folder:
            # Set the current subfolder path entry to the resolved folder
            self.current_subfolder_var.set(resolved_folder)
            # Find the parent 'default' folder of the resolved folder
            parent_default = resolved_folder
            while parent_default and os.path.basename(parent_default) != 'default':
                parent_default = os.path.dirname(parent_default)
            if os.path.basename(parent_default) == 'default':
                self.refresh_subfolder_tabs(parent_default)
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
        # Use normalized comparison for matching
        target = self.mcap_filename_from_link.strip().lower() if self.mcap_filename_from_link else None
        for i, filename in enumerate(self.mcap_files_list):
            self.mcap_listbox.insert(tk.END, filename)
            if target and os.path.basename(filename).strip().lower() == target:
                self.mcap_listbox.itemconfig(i, {'bg':'#FFFF99'}) # Light yellow
                highlight_idx = i
        
        if highlight_idx != -1:
            self.mcap_listbox.selection_set(highlight_idx)
            self.mcap_listbox.see(highlight_idx)
            self.on_file_select(None, suppress_log=True)
        else:
            if self.mcap_filename_from_link:
                self.log_message(f"Note: File from link ('{self.mcap_filename_from_link}') not found in the listed files.")
            self.disable_file_specific_action_buttons()


    def on_file_select(self, event, suppress_log=False): # event can be None
        selection = self.mcap_listbox.curselection()
        if selection:
            self.enable_file_specific_action_buttons()
            if not suppress_log:
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

    def open_foxglove_with_browser(self):
        import webbrowser
        url = "https://foxglove.data.ventitechnologies.net/?ds=remote-file&ds.url=https://rosbag.data.ventitechnologies.net/20250618/PROD/PSA8607/rosbags/default/PSA8607_2025-06-18_13-37-43/PSA8607_2025-06-18-17-27-45_46.mcap"
        webbrowser.open(url)
        self.log_message("Opened Foxglove in browser.")

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
            # Update the current subfolder path entry to match the selected tab
            self.current_subfolder_var.set(self.current_mcap_folder_absolute)
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
            # self.default_folder_var.set(folder) # No longer needed
            self.refresh_subfolder_tabs()

    def refresh_subfolder_tabs(self, default_folder=None):
        # Remove old tabs if any
        if self.subfolder_tabs:
            self.subfolder_tabs.destroy()
            self.subfolder_tabs = None
            self.subfolder_tab_names = []
            self.subfolder_tab_paths = []
        # Always use the parent 'default' folder for subfolder search
        if default_folder is None:
            # Use core logic to resolve the effective default folder
            current_path = self.current_subfolder_var.get() or os.path.expanduser('~/data/default')
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

    # File Explorer Methods
    def refresh_explorer(self):
        """Refresh the file explorer with current directory contents"""
        try:
            self.explorer_listbox.delete(0, tk.END)
            self.explorer_files_list = []
            
            if not os.path.exists(self.current_explorer_path):
                self.log_message(f"Path does not exist: {self.current_explorer_path}", is_error=True)
                return
            
            if not os.path.isdir(self.current_explorer_path):
                self.log_message(f"Path is not a directory: {self.current_explorer_path}", is_error=True)
                return
            
            # Update path display
            self.explorer_path_var.set(self.current_explorer_path)
            
            # Add parent directory option (unless we're at root)
            parent_dir = os.path.dirname(self.current_explorer_path)
            if parent_dir != self.current_explorer_path:  # Not at root
                self.explorer_listbox.insert(tk.END, "⬆️ .. (Parent Directory)")
                self.explorer_files_list.append("..")
            
            # List directories first, then files
            items = os.listdir(self.current_explorer_path)
            dirs = []
            files = []
            
            for item in items:
                if item.startswith('.'):  # Skip hidden files
                    continue
                item_path = os.path.join(self.current_explorer_path, item)
                if os.path.isdir(item_path):
                    dirs.append(item)
                else:
                    files.append(item)
            
            # Sort directories and files separately
            dirs.sort(key=str.lower)
            files.sort(key=str.lower)
            
            # --- Apply search filter ---
            filter_str = self.explorer_search_var.get().strip().lower() if hasattr(self, 'explorer_search_var') else ""
            if filter_str:
                dirs = [d for d in dirs if filter_str in d.lower()]
                files = [f for f in files if filter_str in f.lower()]
            
            view_mode = self.explorer_view_mode.get()
            
            # Add directories
            for d in dirs:
                display_text = self._format_directory_display(d, view_mode)
                self.explorer_listbox.insert(tk.END, display_text)
                self.explorer_files_list.append(d)
            
            # Add files
            for f in files:
                display_text = self._format_file_display(f, view_mode)
                self.explorer_listbox.insert(tk.END, display_text)
                self.explorer_files_list.append(f)
                
        except PermissionError:
            self.log_message(f"Permission denied accessing: {self.current_explorer_path}", is_error=True)
        except Exception as e:
            self.log_message(f"Error refreshing explorer: {e}", is_error=True)

    def _truncate_name(self, name, width=32):
        """Truncate and pad name for table-like alignment"""
        if len(name) > width:
            return name[:width-3] + '...'
        return name.ljust(width)

    def _format_directory_display(self, dirname, view_mode):
        if view_mode == "simple":
            return f"📁 {dirname}"
        elif view_mode == "icons":
            return f"📁\n{dirname[:15]}..." if len(dirname) > 15 else f"📁\n{dirname}"
        else:  # detailed
            dir_path = os.path.join(self.current_explorer_path, dirname)
            try:
                item_count = len([x for x in os.listdir(dir_path) if not x.startswith('.')])
                name_col = self._truncate_name(dirname)
                return f"📁 {name_col}   {'-':>10} {'-':>16}  ({item_count} items)"
            except (PermissionError, OSError):
                name_col = self._truncate_name(dirname)
                return f"📁 {name_col}   {'-':>10} {'-':>16}  (Access denied)"

    def _format_file_display(self, filename, view_mode):
        file_path = os.path.join(self.current_explorer_path, filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.mcap']:
            icon = "🎥"
        elif ext in ['.txt', '.log', '.md']:
            icon = "📄"
        elif ext in ['.py', '.js', '.cpp', '.h', '.c', '.java']:
            icon = "📜"
        elif ext in ['.jpg', '.png', '.gif', '.bmp', '.jpeg']:
            icon = "🖼️"
        elif ext in ['.zip', '.tar', '.gz', '.rar']:
            icon = "📦"
        elif ext in ['.pdf']:
            icon = "📕"
        elif ext in ['.json', '.xml', '.yaml', '.yml']:
            icon = "⚙️"
        else:
            icon = "📄"
        if view_mode == "simple":
            return f"{icon} {filename}"
        elif view_mode == "icons":
            short_name = filename[:12] + "..." if len(filename) > 15 else filename
            return f"{icon}\n{short_name}"
        else:  # detailed
            try:
                size = os.path.getsize(file_path)
                size_str = self._format_file_size(size)
                mod_time = os.path.getmtime(file_path)
                import time
                mod_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mod_time))
                name_col = self._truncate_name(filename)
                return f"{icon} {name_col}   {size_str:>10} {mod_str:>16}"
            except (OSError, PermissionError):
                name_col = self._truncate_name(filename)
                return f"{icon} {name_col}   {'N/A':>10} {'N/A':>16}"

    def _format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def go_back(self):
        """Navigate back in history"""
        if self.explorer_history:
            previous_path = self.explorer_history.pop()
            self.current_explorer_path = previous_path
            self.refresh_explorer()

    def _add_to_history(self, path):
        """Add current path to navigation history"""
        if path != self.current_explorer_path and path not in self.explorer_history[-5:]:
            self.explorer_history.append(self.current_explorer_path)
            # Keep only last 10 entries
            self.explorer_history = self.explorer_history[-10:]

    def go_up_directory(self):
        """Navigate to parent directory"""
        parent_dir = os.path.dirname(self.current_explorer_path)
        if parent_dir != self.current_explorer_path:  # Not at root
            self._add_to_history(self.current_explorer_path)
            self.current_explorer_path = parent_dir
            self.refresh_explorer()

    def go_home_directory(self):
        """Navigate to data directory (~/data)"""
        data_path = os.path.expanduser("~/data")
        if self.current_explorer_path != data_path:
            self._add_to_history(self.current_explorer_path)
            self.current_explorer_path = data_path
            self.refresh_explorer()

    def browse_directory(self):
        """Open directory browser dialog"""
        selected_dir = filedialog.askdirectory(initialdir=self.current_explorer_path)
        if selected_dir:
            self.current_explorer_path = selected_dir
            self.refresh_explorer()

    def navigate_to_path(self, event=None):
        """Navigate to the path in the entry field"""
        new_path = self.explorer_path_var.get().strip()
        if new_path and os.path.exists(new_path) and os.path.isdir(new_path):
            self.current_explorer_path = new_path
            self.refresh_explorer()
        else:
            self.log_message(f"Invalid path: {new_path}", is_error=True)
            self.explorer_path_var.set(self.current_explorer_path)

    def on_explorer_double_click(self, event):
        """Handle double-click on explorer listbox items"""
        selection = self.explorer_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                
                if selected_item == "..":
                    self.go_up_directory()
                else:
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    if os.path.isdir(item_path):
                        self._add_to_history(self.current_explorer_path)
                        self.current_explorer_path = item_path
                        self.refresh_explorer()
                    else:
                        self.open_file(item_path)

    def on_explorer_select(self, event):
        """Handle selection change in explorer listbox"""
        selection = self.explorer_listbox.curselection()
        if selection:
            # Get selected MCAP files
            mcap_files_selected = self.get_selected_explorer_mcap_paths()
            
            # Enable/disable buttons based on selection
            if len(selection) == 1:
                idx = selection[0]
                if idx < len(self.explorer_files_list):
                    selected_item = self.explorer_files_list[idx]
                    if selected_item != "..":
                        item_path = os.path.join(self.current_explorer_path, selected_item)
                        if os.path.isfile(item_path):
                            self.open_file_button.config(state=tk.NORMAL)
                            self.copy_path_button.config(state=tk.NORMAL)
                            
                            # Enable MCAP-specific buttons for .mcap files
                            if item_path.lower().endswith('.mcap'):
                                self.open_with_foxglove_button.config(state=tk.NORMAL)
                                self.open_with_bazel_button.config(state=tk.NORMAL)
                            else:
                                self.open_with_foxglove_button.config(state=tk.DISABLED)
                                self.open_with_bazel_button.config(state=tk.DISABLED)
                        else:
                            self.open_file_button.config(state=tk.DISABLED)
                            self.open_with_foxglove_button.config(state=tk.DISABLED)
                            self.open_with_bazel_button.config(state=tk.DISABLED)
                            self.copy_path_button.config(state=tk.NORMAL)
                    else:
                        self.open_file_button.config(state=tk.DISABLED)
                        self.open_with_foxglove_button.config(state=tk.DISABLED)
                        self.open_with_bazel_button.config(state=tk.DISABLED)
                        self.copy_path_button.config(state=tk.DISABLED)
            else:
                # Multiple selection - disable single file actions
                self.open_file_button.config(state=tk.DISABLED)
                self.open_with_foxglove_button.config(state=tk.DISABLED)
                self.open_with_bazel_button.config(state=tk.DISABLED)
                self.copy_path_button.config(state=tk.DISABLED)
            
            # Enable multiple MCAP button if more than one MCAP is selected
            if len(mcap_files_selected) > 1:
                self.open_multiple_bazel_button.config(state=tk.NORMAL)
            else:
                self.open_multiple_bazel_button.config(state=tk.DISABLED)
                
        else:
            self.open_file_button.config(state=tk.DISABLED)
            self.open_with_foxglove_button.config(state=tk.DISABLED)
            self.open_with_bazel_button.config(state=tk.DISABLED)
            self.open_multiple_bazel_button.config(state=tk.DISABLED)
            self.copy_path_button.config(state=tk.DISABLED)

    def open_selected_file(self):
        """Open the currently selected file"""
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
        """Open a file using the system default application"""
        try:
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdg-open", file_path], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", file_path], check=True)
            elif system == "Windows":
                os.startfile(file_path)
            else:
                self.log_message(f"Unsupported system: {system}", is_error=True)
                return
            
            self.log_message(f"Opened file: {os.path.basename(file_path)}")
        except subprocess.CalledProcessError as e:
            self.log_message(f"Failed to open file: {e}", is_error=True)
        except Exception as e:
            self.log_message(f"Error opening file: {e}", is_error=True)

    def open_in_file_manager(self):
        """Open current directory in system file manager"""
        try:
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdg-open", self.current_explorer_path], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", self.current_explorer_path], check=True)
            elif system == "Windows":
                subprocess.run(["explorer", self.current_explorer_path], check=True)
            else:
                self.log_message(f"Unsupported system: {system}", is_error=True)
                return
            
            self.log_message(f"Opened in file manager: {self.current_explorer_path}")
        except subprocess.CalledProcessError as e:
            self.log_message(f"Failed to open file manager: {e}", is_error=True)
        except Exception as e:
            self.log_message(f"Error opening file manager: {e}", is_error=True)

    def copy_selected_path(self):
        """Copy the path of the selected item to clipboard"""
        selection = self.explorer_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                if selected_item != "..":
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(item_path)
                        self.log_message(f"Copied to clipboard: {item_path}")
                    except Exception as e:
                        self.log_message(f"Error copying to clipboard: {e}", is_error=True)

    def open_with_foxglove(self):
        """Open the selected MCAP file with Foxglove"""
        selection = self.explorer_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                if selected_item != "..":
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    if os.path.isfile(item_path) and item_path.lower().endswith('.mcap'):
                        self.log_message(f"Launching Foxglove with {os.path.basename(item_path)}...")
                        message, error = self.logic.launch_foxglove(item_path)
                        if message: 
                            self.log_message(message)
                        if error: 
                            self.log_message(error, is_error=True)
                    else:
                        self.log_message("Selected file is not an MCAP file.", is_error=True)

    def open_with_bazel(self):
        """Open the selected MCAP file with Bazel Bag GUI"""
        selection = self.explorer_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                if selected_item != "..":
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    if os.path.isfile(item_path) and item_path.lower().endswith('.mcap'):
                        self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(item_path)}...")
                        message, error = self.logic.launch_bazel_bag_gui(item_path)
                        if message: 
                            self.log_message(message)
                        if error: 
                            self.log_message(error, is_error=True)
                    else:
                        self.log_message("Selected file is not an MCAP file.", is_error=True)

    def open_multiple_with_bazel(self):
        """Open multiple selected MCAP files with Bazel Bag GUI using symlinks"""
        mcap_files = self.get_selected_explorer_mcap_paths()
        
        if len(mcap_files) > 1:
            self.log_message(f"Launching Bazel Bag GUI with {len(mcap_files)} selected MCAP files using symlinks...")
            message, error, symlink_dir = self.logic.play_bazel_bag_gui_with_symlinks(mcap_files)
            if message: 
                self.log_message(message)
            if error: 
                self.log_message(error, is_error=True)
        elif len(mcap_files) == 1:
            # Fall back to single file launch
            self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(mcap_files[0])}...")
            message, error = self.logic.launch_bazel_bag_gui(mcap_files[0])
            if message: 
                self.log_message(message)
            if error: 
                self.log_message(error, is_error=True)
        else:
            self.log_message("No MCAP files selected.", is_error=True)

    def get_selected_explorer_mcap_paths(self):
        """Get paths of all selected MCAP files in the explorer"""
        selection = self.explorer_listbox.curselection()
        mcap_paths = []
        
        for idx in selection:
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                if selected_item != "..":
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    if os.path.isfile(item_path) and item_path.lower().endswith('.mcap'):
                        mcap_paths.append(item_path)
        
        return mcap_paths

    def on_explorer_search(self, event=None):
        """Callback for search/filter bar in file explorer"""
        self.refresh_explorer()

    def clear_explorer_search(self):
        self.explorer_search_var.set("")
        self.refresh_explorer()

    def focus_explorer_listbox(self, event=None):
        self.explorer_listbox.focus_set()
        if self.explorer_listbox.size() > 0:
            cur = self.explorer_listbox.curselection()
            if not cur:
                self.explorer_listbox.selection_set(0)
                self.explorer_listbox.activate(0)
        return 'break'

    def select_first_and_focus_listbox(self, event=None):
        if self.explorer_listbox.size() > 0:
            self.explorer_listbox.selection_clear(0, tk.END)
            self.explorer_listbox.selection_set(0)
            self.explorer_listbox.activate(0)
            self.explorer_listbox.focus_set()
            # If the first item is a folder, enter it
            selected_item = self.explorer_files_list[0] if len(self.explorer_files_list) > 0 else None
            if selected_item and selected_item != "..":
                item_path = os.path.join(self.current_explorer_path, selected_item)
                if os.path.isdir(item_path):
                    self._add_to_history(self.current_explorer_path)
                    self.current_explorer_path = item_path
                    self.refresh_explorer()
        return 'break'

    def clear_search_and_focus(self, event=None):
        self.clear_explorer_search()
        self.explorer_search_entry.focus_set()
        return 'break'

    def on_explorer_listbox_enter(self, event=None):
        selection = self.explorer_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                if selected_item == "..":
                    self.go_up_directory()
                else:
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    if os.path.isdir(item_path):
                        self._add_to_history(self.current_explorer_path)
                        self.current_explorer_path = item_path
                        self.clear_explorer_search()  # Clear search bar after entering folder
                        self.refresh_explorer()
                    else:
                        self.open_file(item_path)
        return 'break'

    def on_explorer_listbox_backspace(self, event=None):
        self.go_up_directory()
        return 'break'