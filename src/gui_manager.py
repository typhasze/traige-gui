import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Listbox, Scrollbar, Frame, Label, Entry, Button, Text, END, SINGLE, VERTICAL, HORIZONTAL
import os
import signal
import subprocess
import platform
from core_logic import FoxgloveLogic # Assuming core_logic.py is in the same directory
from logic.file_explorer_logic import FileExplorerLogic
import shutil

class FoxgloveAppGUIManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Foxglove MCAP Launcher")
        self.logic = FoxgloveLogic()
        self.file_explorer_logic = FileExplorerLogic()
        
        self.current_mcap_folder_absolute = None
        self.mcap_filename_from_link = None
        self.mcap_files_list = []
        
        # File explorer variables
        self.current_explorer_path = os.path.expanduser("~/data")
        self.explorer_files_list = []
        self.explorer_view_mode = tk.StringVar(value="detailed")  # detailed, simple, icons
        self.explorer_history = []  # Navigation history

        self.create_widgets()
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
        # Create Settings tab
        self.settings_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.settings_frame, text="Settings")

        # Create file actions frame that's shared between tabs
        self.create_file_actions_frame(main_frame)

        # Create widgets for each tab
        self.create_foxglove_widgets()
        self.create_explorer_widgets()
        self.create_settings_widgets()

        # Set up logging frame that's shared between tabs
        self.create_shared_log_frame(main_frame)

        # Cache tab indices for performance
        self._cache_tab_indices()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_signal_handlers()
        # Now that all widgets are created, refresh explorer
        self.refresh_explorer()
        # Bind tab change event to update button states
        self.main_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def create_file_actions_frame(self, parent_frame):
        # --- File Actions Frame ---
        file_actions_frame = ttk.LabelFrame(parent_frame, text="File Actions", padding="10")
        file_actions_frame.pack(padx=5, pady=5, fill="x")

        # All file action buttons in one frame
        self.open_file_button = self._create_button(file_actions_frame, "Open w/ Default", self.open_selected_file, state=tk.DISABLED)
        self.launch_foxglove_button = self._create_button(file_actions_frame, "Foxglove Playback", self.open_with_foxglove, state=tk.DISABLED)
        self.launch_bazel_gui_button = self._create_button(file_actions_frame, "Bazel Playback", self.open_with_bazel, state=tk.DISABLED)
        self.launch_bazel_viz_button = self._create_button(file_actions_frame, "Visualizer", self.launch_bazel_viz)
        self.open_folder_button = self._create_button(file_actions_frame, "File Manager", self.open_in_file_manager)
        self.copy_path_button = self._create_button(file_actions_frame, "Copy Path", self.copy_selected_path, state=tk.DISABLED)

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
        # --- Navigation Frame ---
        nav_frame = ttk.LabelFrame(self.explorer_frame, text="Navigation", padding="10")
        nav_frame.pack(padx=5, pady=5, fill="x")

        # Path entry and navigation buttons
        path_frame = ttk.Frame(nav_frame)
        path_frame.pack(fill="x")
        ttk.Label(path_frame, text="Path:").pack(side=tk.LEFT, padx=(0,5))
        self.explorer_path_var = tk.StringVar(value=self.current_explorer_path)
        self.explorer_path_entry = ttk.Entry(path_frame, textvariable=self.explorer_path_var, width=50)
        self.explorer_path_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0,5))
        self.explorer_path_entry.bind('<Return>', self.navigate_to_path)
        
        # Navigation buttons
        ttk.Button(path_frame, text="Go", command=self.navigate_to_path).pack(side=tk.LEFT)
        ttk.Button(path_frame, text="Home", command=self.go_home_directory).pack(side=tk.LEFT, padx=(5,0))

        # --- Search Frame ---
        search_frame = ttk.LabelFrame(self.explorer_frame, text="Search", padding="10")
        search_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Label(search_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.explorer_search_var = tk.StringVar()
        self.explorer_search_var.trace_add('write', self.on_explorer_search)
        self.explorer_search_entry = ttk.Entry(search_frame, textvariable=self.explorer_search_var, width=30)
        self.explorer_search_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.explorer_search_entry.bind('<Escape>', self._on_explorer_search_escape)
        self.explorer_search_entry.bind('<Up>', self.focus_explorer_listbox_up)
        self.explorer_search_entry.bind('<Down>', self.focus_explorer_listbox_down)

        # --- Files and Folders List Frame ---
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
        
        # Bind events
        self.explorer_listbox.bind('<Double-Button-1>', self.on_explorer_double_click)
        self.explorer_listbox.bind('<<ListboxSelect>>', self.on_explorer_select)
        self.explorer_listbox.bind('<Return>', self.on_explorer_enter_key)
        self.explorer_listbox.bind('<KP_Enter>', self.on_explorer_enter_key)
        self.explorer_listbox.bind('<BackSpace>', self.on_explorer_backspace_key)
        self.explorer_listbox.bind('<Key>', self._focus_search_on_typing)

        # Bind ESC to clear search from anywhere in explorer tab
        self.explorer_frame.bind_all('<Escape>', self._on_explorer_search_escape, add='+')

    def _focus_search_on_typing(self, event):
        """If a printable key is pressed in the listbox, focus the search bar and type the char."""
        if event.char and event.char.isprintable() and not event.state & 0x4:  # ignore Ctrl
            self.explorer_search_entry.focus_set()
            # Insert the char at the end of the search bar
            current = self.explorer_search_var.get()
            # If search bar is not empty and selection, replace selection
            if self.explorer_search_entry.selection_present():
                self.explorer_search_entry.delete('sel.first', 'sel.last')
            self.explorer_search_entry.insert(tk.END, event.char)
            # Move cursor to end
            self.explorer_search_entry.icursor(tk.END)
            return 'break'
        # Allow navigation keys to work as normal
        return None

    def _on_explorer_search_escape(self, event=None):
        """Clear the explorer search bar on ESC."""
        self.explorer_search_var.set("")
        return 'break'

    def refresh_explorer(self):
        """Refresh the file explorer with current directory contents, applying search filter if set"""
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
            # Use FileExplorerLogic to list directories and files
            dirs, files = self.file_explorer_logic.list_directory(self.current_explorer_path)
            # Apply search filter if set
            search_query = self.explorer_search_var.get().strip().lower() if hasattr(self, 'explorer_search_var') else ''
            if search_query:
                dirs = [d for d in dirs if search_query in d.lower()]
                files = [f for f in files if search_query in f.lower()]
            for d in dirs:
                self.explorer_listbox.insert(tk.END, f"📁 {d}")
                self.explorer_files_list.append(d)
            for f in files:
                info = self.file_explorer_logic.get_file_info(os.path.join(self.current_explorer_path, f))
                icon = info['icon'] if 'icon' in info else ''
                self.explorer_listbox.insert(tk.END, f"{icon} {f}")
                self.explorer_files_list.append(f)
        except PermissionError:
            self.log_message(f"Permission denied accessing: {self.current_explorer_path}", is_error=True)
        except Exception as e:
            self.log_message(f"Error refreshing explorer: {e}", is_error=True)

    def on_explorer_search(self, *args):
        """Callback for search bar: refresh explorer with filter applied and highlight first directory if present"""
        self.refresh_explorer()
        # Only auto-select if the search bar has focus and the listbox does not have focus or selection
        focus_widget = self.root.focus_get()
        listbox_has_focus = focus_widget == self.explorer_listbox
        selection = self.explorer_listbox.curselection()
        if self.root.focus_get() == self.explorer_search_entry and not listbox_has_focus and not selection:
            if self.explorer_listbox.size() > 0:
                first_idx = 0
                if self.explorer_files_list and self.explorer_files_list[0] == "..":
                    if len(self.explorer_files_list) > 1:
                        first_idx = 1
                    else:
                        return  # Only parent dir present
                self.explorer_listbox.selection_clear(0, tk.END)
                self.explorer_listbox.selection_set(first_idx)
                self.explorer_listbox.see(first_idx)

    def create_settings_widgets(self):
        settings_frame = self.settings_frame
        # Bazel Working Directory (move to top)
        ttk.Label(settings_frame, text="Bazel Working Directory:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.bazel_working_dir_var = tk.StringVar(value=self.logic.get_bazel_working_dir())
        self.bazel_working_dir_entry = ttk.Entry(settings_frame, textvariable=self.bazel_working_dir_var, width=60)
        self.bazel_working_dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # Bazel Tools Viz command
        ttk.Label(settings_frame, text="Bazel Tools Viz Command:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.bazel_tools_viz_var = tk.StringVar(value=' '.join(self.logic.get_bazel_tools_viz_cmd()))
        self.bazel_tools_viz_entry = ttk.Entry(settings_frame, textvariable=self.bazel_tools_viz_var, width=60)
        self.bazel_tools_viz_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        # Bazel Bag GUI command
        ttk.Label(settings_frame, text="Bazel Bag GUI Command:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.bazel_bag_gui_var = tk.StringVar(value=' '.join(self.logic.get_bazel_bag_gui_cmd()))
        self.bazel_bag_gui_entry = ttk.Entry(settings_frame, textvariable=self.bazel_bag_gui_var, width=60)
        self.bazel_bag_gui_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        # Save and Reset buttons (move to row 3)
        btn_frame = ttk.Frame(settings_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset_settings).pack(side=tk.LEFT, padx=5)
        settings_frame.columnconfigure(1, weight=1)

    def save_settings(self):
        # Split command string into list for each
        viz_cmd = self.bazel_tools_viz_var.get().strip().split()
        bag_cmd = self.bazel_bag_gui_var.get().strip().split()
        working_dir = self.bazel_working_dir_var.get().strip()
        ok1, err1 = self.logic.set_bazel_tools_viz_cmd(viz_cmd)
        ok2, err2 = self.logic.set_bazel_bag_gui_cmd(bag_cmd)
        ok3, err3 = self.logic.set_bazel_working_dir(working_dir)
        if ok1 and ok2 and ok3:
            self.log_message("Settings saved.")
        else:
            self.log_message(f"Error saving settings: {err1 or ''} {err2 or ''} {err3 or ''}", is_error=True)

    def reset_settings(self):
        self.logic.settings = self.logic.load_settings()
        self.bazel_tools_viz_var.set(' '.join(self.logic.get_bazel_tools_viz_cmd()))
        self.bazel_bag_gui_var.set(' '.join(self.logic.get_bazel_bag_gui_cmd()))
        self.bazel_working_dir_var.set(self.logic.get_bazel_working_dir())
        self.log_message("Settings reset to last saved.")

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

    def disable_file_specific_action_buttons(self):
        self.launch_foxglove_button.config(state=tk.DISABLED)
        self.launch_bazel_gui_button.config(state=tk.DISABLED)

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

    def _create_button(self, parent, text, command, state=tk.NORMAL, **pack_opts):
        """Helper to create and pack a ttk.Button with common options."""
        btn = ttk.Button(parent, text=text, command=command, state=state)
        btn.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x", **pack_opts)
        return btn

    # File Explorer Methods
    def refresh_explorer(self, event=None):
        """Refresh the file explorer with current directory contents, applying search filter if set"""
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
            
            # Use FileExplorerLogic to list directories and files
            dirs, files = self.file_explorer_logic.list_directory(self.current_explorer_path)
            
            # Apply search filter if set - optimize by checking once
            search_query = getattr(self, 'explorer_search_var', None)
            if search_query:
                search_text = search_query.get().strip().lower()
                if search_text:
                    dirs = [d for d in dirs if search_text in d.lower()]
                    files = [f for f in files if search_text in f.lower()]
            
            # Batch process directories
            for d in dirs:
                self.explorer_listbox.insert(tk.END, f"📁 {d}")
                self.explorer_files_list.append(d)
            
            # Batch process files with file info lookup
            for f in files:
                item_path = os.path.join(self.current_explorer_path, f)
                info = self.file_explorer_logic.get_file_info(item_path)
                icon = info.get('icon', '')
                self.explorer_listbox.insert(tk.END, f"{icon} {f}")
                self.explorer_files_list.append(f)
                
        except PermissionError:
            self.log_message(f"Permission denied accessing: {self.current_explorer_path}", is_error=True)
        except Exception as e:
            self.log_message(f"Error refreshing explorer: {e}", is_error=True)

    def _format_directory_display(self, dirname, view_mode):
        # No longer used
        return dirname

    def _format_file_display(self, filename, view_mode):
        # No longer used
        return filename

    def get_selected_explorer_mcap_paths(self):
        """Get paths of all selected MCAP files in the explorer - optimized version"""
        selection = self.explorer_listbox.curselection()
        if not selection:
            return []
        
        mcap_paths = []
        files_list_len = len(self.explorer_files_list)
        
        for idx in selection:
            if idx >= files_list_len:
                continue
                
            selected_item = self.explorer_files_list[idx]
            if selected_item == "..":
                continue
                
            item_path = os.path.join(self.current_explorer_path, selected_item)
            if os.path.isfile(item_path) and self.file_explorer_logic.is_mcap_file(item_path):
                mcap_paths.append(item_path)
        
        return mcap_paths

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
        """Navigate to parent directory, but do not go above ~/data"""
        data_root = os.path.expanduser('~/data')
        # Normalize paths for comparison
        current = os.path.abspath(self.current_explorer_path)
        data_root = os.path.abspath(data_root)
        parent_dir = os.path.dirname(current)
        # Prevent navigating above ~/data
        if os.path.normpath(current) == os.path.normpath(data_root):
            # Already at ~/data, do nothing
            return
        if os.path.commonpath([parent_dir, data_root]) != data_root:
            # Parent is above ~/data, do nothing
            return
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

    def explorer_navigate_selected(self):
        """Navigate into directory or open file for the currently selected item in explorer_listbox."""
        selection = self.explorer_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                if selected_item == "..":
                    self.go_up_directory()
                    self.clear_explorer_search()  # Clear search bar on directory navigation
                else:
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    if os.path.isdir(item_path):
                        # Prevent navigating above ~/data
                        data_path = os.path.expanduser("~/data")
                        abs_item_path = os.path.abspath(item_path)
                        if abs_item_path == os.path.abspath(data_path) or abs_item_path.startswith(os.path.abspath(data_path) + os.sep):
                            self._add_to_history(self.current_explorer_path)
                            self.current_explorer_path = item_path
                            self.refresh_explorer()
                        else:
                            # If trying to go above ~/data, stay at ~/data
                            self._add_to_history(self.current_explorer_path)
                            self.current_explorer_path = data_path
                            self.refresh_explorer()
                        self.clear_explorer_search()  # Clear search bar on directory navigation
                    else:
                        self.open_file(item_path)

    def on_explorer_double_click(self, event):
        """Handle double-click on explorer listbox items"""
        self.explorer_navigate_selected()

    def on_explorer_enter_key(self, event):
        """Handle Enter key in explorer listbox: enter directory or open file"""
        self.explorer_navigate_selected()

    def on_explorer_backspace_key(self, event):
        """Handle Backspace key in explorer listbox: go up directory and clear search bar"""
        self.go_up_directory()
        self.clear_explorer_search()

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
        """Open a file using the system default application via FileExplorerLogic"""
        success, msg = self.file_explorer_logic.open_file(file_path)
        if success:
            self.log_message(msg)
        else:
            self.log_message(msg, is_error=True)

    def open_in_file_manager(self):
        """Open current directory in system file manager via FileExplorerLogic"""
        success, msg = self.file_explorer_logic.open_in_file_manager(self.current_explorer_path)
        if success:
            self.log_message(msg)
        else:
            self.log_message(msg, is_error=True)

    def copy_selected_path(self):
        """Copy the path of the selected item to clipboard via FileExplorerLogic"""
        selection = self.explorer_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                if selected_item != "..":
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    success, msg = self.file_explorer_logic.copy_to_clipboard(self.root, item_path)
                    if success:
                        self.log_message(msg)
                    else:
                        self.log_message(msg, is_error=True)

    def open_with_foxglove(self):
        """Open the selected MCAP file with Foxglove from either tab."""
        current_tab = self.main_notebook.index(self.main_notebook.select())
        
        if current_tab == self._explorer_tab_index:
            # File Explorer tab: use explorer selection
            mcap_files = self.get_selected_explorer_mcap_paths()
            if not mcap_files:
                self.log_message("No MCAP file selected in File Explorer.", is_error=True)
                return
            file_path = mcap_files[-1]
        elif current_tab == self._foxglove_tab_index:
            # Foxglove MCAP tab: use MCAP list selection
            file_path = self.get_selected_mcap_path()
            if not file_path:
                self.log_message("No MCAP file selected in Foxglove MCAP tab.", is_error=True)
                return
        else:
            self.log_message("Open with Foxglove is only available in File Explorer or Foxglove MCAP tabs.", is_error=True)
            return
        self.log_message(f"Launching Foxglove with {os.path.basename(file_path)}...")
        message, error = self.logic.launch_foxglove(file_path)
        if message:
            self.log_message(message)
        if error:
            self.log_message(error, is_error=True)

    def open_with_bazel(self):
        """Open the selected MCAP file(s) with Bazel Bag GUI from either tab."""
        current_tab = self.main_notebook.index(self.main_notebook.select())
        
        if current_tab == self._explorer_tab_index:
            mcap_files = self.get_selected_explorer_mcap_paths()
            if not mcap_files:
                self.log_message("No MCAP file selected in File Explorer.", is_error=True)
                return
            
            # Handle multiple file selection
            if len(mcap_files) == 1:
                self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(mcap_files[0])}...")
                message, error = self.logic.launch_bazel_bag_gui(mcap_files[0])
                if message:
                    self.log_message(message)
                if error:
                    self.log_message(error, is_error=True)
            else:
                self.log_message(f"Launching Bazel Bag GUI with {len(mcap_files)} selected MCAP files using symlinks...")
                message, error, symlink_dir = self.logic.play_bazel_bag_gui_with_symlinks(mcap_files)
                if message:
                    self.log_message(message)
                if error:
                    self.log_message(error, is_error=True)
                    
        elif current_tab == self._foxglove_tab_index:
            # For Foxglove tab, get all selected files (multiple selection supported)
            selected_paths = self.get_selected_mcap_paths()
            if not selected_paths:
                self.log_message("No MCAP file selected in Foxglove MCAP tab.", is_error=True)
                return
            
            if len(selected_paths) == 1:
                self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(selected_paths[0])}...")
                message, error = self.logic.launch_bazel_bag_gui(selected_paths[0])
                if message:
                    self.log_message(message)
                if error:
                    self.log_message(error, is_error=True)
            else:
                self.log_message(f"Launching Bazel Bag GUI with {len(selected_paths)} selected MCAP files using symlinks...")
                message, error, symlink_dir = self.logic.play_bazel_bag_gui_with_symlinks(selected_paths)
                if message:
                    self.log_message(message)
                if error:
                    self.log_message(error, is_error=True)
        else:
            self.log_message("Open with Bazel is only available in File Explorer or Foxglove MCAP tabs.", is_error=True)
            return

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

    def on_explorer_select(self, event, suppress_log=False):
        """Handle selection change in explorer listbox (enables/disables file action buttons)."""
        selection = self.explorer_listbox.curselection()
        
        # Default: all actions disabled
        states = {
            "open_file": False,
            "copy_path": False,
            "open_with_foxglove": False,
            "open_with_bazel": False
        }
        
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_files_list):
                selected_item = self.explorer_files_list[idx]
                if selected_item != "..":
                    item_path = os.path.join(self.current_explorer_path, selected_item)
                    states = self.file_explorer_logic.get_file_action_states(item_path, False)
                # For parent directory, keep all states as False (already set above)
        
        # Get selected MCAP files for logging (only if not suppressing log)
        if not suppress_log:
            mcap_files = self.get_selected_explorer_mcap_paths()
            if mcap_files:
                self.log_message(f"Selected {len(mcap_files)} bag(s).", clear_first=False)
        
        # Batch update button states
        self._update_button_states(states)

    def clear_explorer_search(self):
        """Clear the explorer search bar."""
        self.explorer_search_var.set("")
        return 'break'

    def _focus_explorer_listbox_move(self, direction, event=None):
        """Move focus to listbox and select previous/next item based on direction (-1 for up, 1 for down)."""
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
        """Move focus to listbox and select previous item."""
        return self._focus_explorer_listbox_move(-1, event)

    def focus_explorer_listbox_down(self, event=None):
        """Move focus to listbox and select next item."""
        return self._focus_explorer_listbox_move(1, event)

    def on_tab_changed(self, event=None):
        """Update file action button states when switching tabs."""
        current_tab = self.main_notebook.index(self.main_notebook.select())
        
        if current_tab == self._explorer_tab_index:
            # File Explorer tab: update based on explorer selection (suppress logging to avoid spam)
            self.on_explorer_select(None, suppress_log=True)
        elif current_tab == self._foxglove_tab_index:
            # Foxglove MCAP tab: update based on MCAP list selection
            self.on_file_select(None, suppress_log=True)
        else:
            # Other tabs: disable all file-specific action buttons
            self.disable_file_specific_action_buttons()

    def _cache_tab_indices(self):
        """Cache tab indices for performance optimization"""
        self._explorer_tab_index = self.main_notebook.tabs().index(str(self.explorer_frame))
        self._foxglove_tab_index = self.main_notebook.tabs().index(str(self.foxglove_frame))
        self._settings_tab_index = self.main_notebook.tabs().index(str(self.settings_frame))

    def _update_button_states(self, states):
        """Efficiently update multiple button states at once"""
        button_mappings = {
            "open_file": self.open_file_button,
            "copy_path": self.copy_path_button,
            "open_with_foxglove": self.launch_foxglove_button,
            "open_with_bazel": self.launch_bazel_gui_button
        }
        
        for state_key, button in button_mappings.items():
            button.config(state=tk.NORMAL if states.get(state_key, False) else tk.DISABLED)