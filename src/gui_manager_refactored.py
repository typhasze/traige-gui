import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import signal
import subprocess
import platform
import shutil
import sys

# Import core logic
from core_logic import FoxgloveLogic

# Import business logic modules
from logic.file_explorer_logic import FileExplorerLogic
from logic.foxglove_logic import FoxgloveLogic as FoxgloveLogicModule
from logic.mcap_logic import McapLogic
from logic.navigation_logic import NavigationLogic

# Import GUI components
from gui.logging_component import LoggingComponent
from gui.file_list_component import FileListComponent
from gui.button_group import ButtonGroup

# Import utilities
from utils.path_utils import normalize_path, format_path_for_display


class FoxgloveAppGUIManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Foxglove MCAP Launcher")
        
        # Initialize core logic
        self.logic = FoxgloveLogic()
        
        # Initialize business logic modules
        self.file_explorer_logic = FileExplorerLogic()
        self.foxglove_logic = FoxgloveLogicModule(self.logic)
        self.mcap_logic = McapLogic(self.logic)
        self.navigation_logic = NavigationLogic(os.path.expanduser("~/data"))
        
        # State variables
        self.current_mcap_folder_absolute = None
        self.mcap_filename_from_link = None
        self.explorer_view_mode = tk.StringVar(value="detailed")
        
        # GUI components
        self.logger = None
        self.mcap_file_list = None
        self.explorer_file_list = None
        self.foxglove_buttons = None
        self.explorer_buttons = None
        
        # Subfolder tabs management
        self.subfolder_tabs = None
        self.subfolder_tab_names = []
        self.subfolder_tab_paths = []
        
        self.create_widgets()
        self.setup_event_handlers()
        self.root.minsize(800, 600)

    def create_widgets(self):
        """Create the main GUI structure"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create main tab system
        self.main_notebook = ttk.Notebook(main_frame)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.foxglove_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.foxglove_frame, text="Foxglove MCAP")
        
        self.explorer_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.explorer_frame, text="File Explorer")

        # Create tab content
        self.create_foxglove_tab()
        self.create_explorer_tab()
        
        # Create shared logging component
        self.logger = LoggingComponent(main_frame)

    def create_foxglove_tab(self):
        """Create the Foxglove tab content"""
        # Input frame for Foxglove link
        self.create_foxglove_input_frame()
        
        # MCAP file list
        self.mcap_file_list = FileListComponent(
            self.foxglove_frame, 
            title="MCAP Files", 
            height=10,
            on_select=self.on_mcap_file_select
        )
        
        # Action buttons for Foxglove
        self.foxglove_buttons = ButtonGroup(self.foxglove_frame, "Launch Actions")
        self.foxglove_buttons.add_button("foxglove", "Open with Foxglove", 
                                       self.launch_foxglove_selected, tk.DISABLED)
        self.foxglove_buttons.add_button("browser", "Open Foxglove with Browser", 
                                       self.open_foxglove_with_browser, tk.NORMAL)
        self.foxglove_buttons.add_button("bazel_gui", "Open with Bazel Bag GUI", 
                                       self.launch_bazel_gui_selected, tk.DISABLED)
        self.foxglove_buttons.add_button("bazel_viz", "Launch Bazel Tools Viz", 
                                       self.launch_bazel_viz, tk.NORMAL)
        self.foxglove_buttons.add_button("launch_all", "Launch All for Selected", 
                                       self.launch_all_selected, tk.DISABLED)
        
        # Current folder display
        self.create_folder_display_frame()
        
        # Initialize subfolder tabs
        self.refresh_subfolder_tabs()

    def create_foxglove_input_frame(self):
        """Create the Foxglove link input frame"""
        input_frame = ttk.LabelFrame(self.foxglove_frame, text="Foxglove Link Analysis", padding="10")
        input_frame.pack(padx=5, pady=5, fill="x")

        ttk.Label(input_frame, text="Foxglove Link:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.link_entry = ttk.Entry(input_frame, width=60)
        self.link_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.link_entry.bind('<Control-a>', self._select_all_text)
        self.link_entry.bind('<Control-A>', self._select_all_text)
        
        self.analyze_button = ttk.Button(input_frame, text="Analyze Link", command=self.analyze_link)
        self.analyze_button.grid(row=0, column=2, padx=5, pady=5)
        
        input_frame.columnconfigure(1, weight=1)

    def create_folder_display_frame(self):
        """Create the folder path display frame"""
        folder_select_frame = ttk.Frame(self.foxglove_frame)
        folder_select_frame.pack(padx=5, pady=(0, 5), fill="x")
        
        ttk.Label(folder_select_frame, text="Current folder path:").pack(side=tk.LEFT)
        
        self.current_subfolder_var = tk.StringVar()
        self.current_subfolder_entry = ttk.Entry(
            folder_select_frame, 
            textvariable=self.current_subfolder_var, 
            width=60, 
            state="readonly"
        )
        self.current_subfolder_entry.pack(side=tk.LEFT, padx=5, fill="x", expand=True)
        self.current_subfolder_entry.bind('<Control-a>', self._select_all_text)
        self.current_subfolder_entry.bind('<Control-A>', self._select_all_text)
        
        self.current_subfolder_var.set("")

    def create_explorer_tab(self):
        """Create the File Explorer tab content"""
        # Navigation frame
        self.create_explorer_navigation_frame()
        
        # File list for explorer
        self.explorer_file_list = FileListComponent(
            self.explorer_frame, 
            title="Files and Folders", 
            height=15,
            on_select=self.on_explorer_select
        )
        
        # Bind additional events for explorer
        self.explorer_file_list.bind_event('<Double-Button-1>', self.on_explorer_double_click)
        self.explorer_file_list.bind_event('<Return>', self.on_explorer_enter_key)
        self.explorer_file_list.bind_event('<KP_Enter>', self.on_explorer_enter_key)
        self.explorer_file_list.bind_event('<BackSpace>', self.on_explorer_backspace_key)
        
        # Action buttons for explorer
        self.explorer_buttons = ButtonGroup(self.explorer_frame, "File Actions")
        self.explorer_buttons.add_button("open_file", "Open File", 
                                        self.open_selected_file, tk.DISABLED)
        self.explorer_buttons.add_button("open_foxglove", "Open with Foxglove", 
                                        self.open_with_foxglove, tk.DISABLED)
        self.explorer_buttons.add_button("open_bazel", "Open with Bazel", 
                                        self.open_with_bazel, tk.DISABLED)
        self.explorer_buttons.add_button("open_multiple", "Open Multiple with Bazel", 
                                        self.open_multiple_with_bazel, tk.DISABLED)
        self.explorer_buttons.add_button("file_manager", "Open in File Manager", 
                                        self.open_in_file_manager, tk.NORMAL)
        self.explorer_buttons.add_button("copy_path", "Copy Path", 
                                        self.copy_selected_path, tk.DISABLED)
        
        # Load initial directory
        self.refresh_explorer()

    def create_explorer_navigation_frame(self):
        """Create the explorer navigation frame"""
        nav_frame = ttk.Frame(self.explorer_frame)
        nav_frame.pack(fill="x", padx=5, pady=5)
        
        # Navigation buttons
        nav_buttons_frame = ttk.Frame(nav_frame)
        nav_buttons_frame.pack(fill="x", pady=(0, 5))
        
        # Only keep Data button
        ttk.Button(nav_buttons_frame, text="💾 Data", 
                  command=self.go_home_directory).pack(side=tk.LEFT, padx=(0, 5))
        
        # View options
        view_frame = ttk.LabelFrame(nav_buttons_frame, text="View", padding="5")
        view_frame.pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Radiobutton(view_frame, text="📋 Detailed", variable=self.explorer_view_mode, 
                       value="detailed", command=self.refresh_explorer).pack(side=tk.LEFT)
        ttk.Radiobutton(view_frame, text="📄 Simple", variable=self.explorer_view_mode, 
                       value="simple", command=self.refresh_explorer).pack(side=tk.LEFT)
        ttk.Radiobutton(view_frame, text="🗂️ Icons", variable=self.explorer_view_mode, 
                       value="icons", command=self.refresh_explorer).pack(side=tk.LEFT)
        
        # Current path display
        path_frame = ttk.Frame(nav_frame)
        path_frame.pack(fill="x")
        
        ttk.Label(path_frame, text="Path:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.explorer_path_var = tk.StringVar(value=self.navigation_logic.get_current_path())
        self.explorer_path_entry = ttk.Entry(path_frame, textvariable=self.explorer_path_var, width=50)
        self.explorer_path_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
        self.explorer_path_entry.bind('<Return>', self.navigate_to_path)
        
        ttk.Button(path_frame, text="Go", command=self.navigate_to_path).pack(side=tk.LEFT)

    def setup_event_handlers(self):
        """Setup event handlers and signal handlers"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """Setup signal handlers for clean shutdown"""
        def handler(signum, frame):
            self.on_closing()
            sys.exit(0)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    # Utility methods
    @staticmethod
    def _select_all_text(event):
        """Select all text in an entry widget"""
        event.widget.focus_set()
        event.widget.select_range(0, 'end')
        return 'break'

    def log_message(self, message, is_error=False, clear_first=False):
        """Log a message using the logger component"""
        if self.logger:
            self.logger.log_message(message, is_error, clear_first)

    # Foxglove tab methods
    def analyze_link(self):
        """Analyze the Foxglove link and update the UI"""
        link = self.link_entry.get()
        if not link:
            self.log_message("Please enter a Foxglove link.", is_error=True, clear_first=True)
            return

        self.log_message(f"Analyzing link: {link}", clear_first=True)
        
        extracted_remote_folder, mcap_filename, local_folder_path = self.foxglove_logic.analyze_foxglove_link(link)
        
        if not extracted_remote_folder or not mcap_filename:
            self.log_message("Could not extract MCAP details from the link.", is_error=True)
            self.clear_mcap_file_list_and_disable_buttons()
            return

        self.log_message(f"Extracted remote folder: {extracted_remote_folder}")
        self.log_message(f"MCAP file from link: {mcap_filename}")
        self.log_message(f"Mapped local folder: {local_folder_path}")

        self.current_mcap_folder_absolute = local_folder_path
        self.mcap_filename_from_link = mcap_filename
        
        # Update UI
        display_folder_name = os.path.basename(local_folder_path) if local_folder_path else "N/A"
        self.mcap_file_list.set_label_text(f"Files in: {display_folder_name} (Full path: {local_folder_path})")
        
        # Get MCAP files and populate list
        mcap_files_list, error = self.mcap_logic.get_mcap_files_in_folder(local_folder_path)
        if error:
            self.log_message(error, is_error=True)
            self.clear_mcap_file_list_and_disable_buttons()
            return
        
        if not mcap_files_list:
            self.log_message("No .mcap files found in the directory.", is_error=True)
            self.clear_mcap_file_list_and_disable_buttons()
            return

        # Populate file list and highlight target
        target_found = self.mcap_file_list.populate_files(mcap_files_list, mcap_filename)
        
        if target_found:
            self.on_mcap_file_select(None, suppress_log=True)
        else:
            if mcap_filename:
                self.log_message(f"Note: File from link ('{mcap_filename}') not found in the listed files.")
            self.disable_mcap_action_buttons()

        # Update folder path display and tabs
        self.current_subfolder_var.set(local_folder_path)
        self.update_subfolder_tabs_for_link(local_folder_path)

    def update_subfolder_tabs_for_link(self, resolved_folder):
        """Update subfolder tabs when analyzing a link"""
        if resolved_folder:
            # Find the parent 'default' folder
            parent_default = resolved_folder
            while parent_default and os.path.basename(parent_default) != 'default':
                parent_default = os.path.dirname(parent_default)
            
            if os.path.basename(parent_default) == 'default':
                self.refresh_subfolder_tabs(parent_default)
                # Try to select the correct tab
                if self.subfolder_tabs and resolved_folder in self.subfolder_tab_paths:
                    idx = self.subfolder_tab_paths.index(resolved_folder)
                    self.subfolder_tabs.select(idx)

    def clear_mcap_file_list_and_disable_buttons(self):
        """Clear the MCAP file list and disable action buttons"""
        if self.mcap_file_list:
            self.mcap_file_list.clear_files()
        self.disable_mcap_action_buttons()

    def on_mcap_file_select(self, event, suppress_log=False):
        """Handle MCAP file selection"""
        if not self.mcap_file_list:
            return
            
        selection = self.mcap_file_list.get_selected_indices()
        if selection:
            self.enable_mcap_action_buttons()
            if not suppress_log:
                self.log_message(f"Selected {len(selection)} bag(s).")
        else:
            self.disable_mcap_action_buttons()

    def enable_mcap_action_buttons(self):
        """Enable MCAP-related action buttons"""
        if self.foxglove_buttons:
            self.foxglove_buttons.enable_button("foxglove")
            self.foxglove_buttons.enable_button("bazel_gui")
            self.foxglove_buttons.enable_button("launch_all")

    def disable_mcap_action_buttons(self):
        """Disable MCAP-related action buttons"""
        if self.foxglove_buttons:
            self.foxglove_buttons.disable_button("foxglove")
            self.foxglove_buttons.disable_button("bazel_gui")
            self.foxglove_buttons.disable_button("launch_all")

    # Foxglove action methods
    def launch_foxglove_selected(self):
        """Launch Foxglove with selected MCAP file"""
        if not self.mcap_file_list or not self.current_mcap_folder_absolute:
            return
            
        selected_paths = self.mcap_logic.get_selected_mcap_paths(
            self.mcap_file_list.listbox, 
            self.current_mcap_folder_absolute
        )
        
        if not selected_paths:
            self.log_message("No MCAP file selected.", is_error=True)
            return
            
        last_path = selected_paths[-1]
        self.log_message(f"Launching Foxglove with {os.path.basename(last_path)}...")
        
        message, error = self.foxglove_logic.launch_foxglove_with_file(last_path)
        if message:
            self.log_message(message)
        if error:
            self.log_message(error, is_error=True)

    def launch_bazel_gui_selected(self):
        """Launch Bazel GUI with selected MCAP files"""
        if not self.mcap_file_list or not self.current_mcap_folder_absolute:
            return
            
        selected_paths = self.mcap_logic.get_selected_mcap_paths(
            self.mcap_file_list.listbox, 
            self.current_mcap_folder_absolute
        )
        
        if not selected_paths:
            self.log_message("No MCAP file(s) selected.", is_error=True)
            return
            
        if len(selected_paths) == 1:
            self.log_message(f"Launching Bazel Bag GUI for {os.path.basename(selected_paths[0])}...")
            message, error = self.mcap_logic.launch_bazel_with_file(selected_paths[0])
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
        else:
            self.log_message(f"Launching Bazel Bag GUI for {len(selected_paths)} selected bags using symlinks...")
            message, error, symlink_dir = self.mcap_logic.launch_bazel_with_multiple_files(selected_paths)
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)

    def launch_bazel_viz(self):
        """Launch Bazel Tools Viz"""
        self.log_message("Launching Bazel Tools Viz...")
        message, error = self.mcap_logic.launch_bazel_viz()
        if message:
            self.log_message(message)
        if error:
            self.log_message(error, is_error=True)

    def launch_all_selected(self):
        """Launch all tools for selected MCAP file"""
        if not self.mcap_file_list or not self.current_mcap_folder_absolute:
            return
            
        selected_path = self.mcap_logic.get_first_selected_mcap_path(
            self.mcap_file_list.listbox,
            self.current_mcap_folder_absolute
        )
        
        if not selected_path:
            self.log_message("No MCAP file selected.", is_error=True)
            return
            
        self.log_message(f"Launching all tools for {os.path.basename(selected_path)}...")
        
        # Launch Foxglove
        msg_fox, err_fox = self.foxglove_logic.launch_foxglove_with_file(selected_path)
        if msg_fox:
            self.log_message(f"Foxglove: {msg_fox}")
        if err_fox:
            self.log_message(f"Foxglove: {err_fox}", is_error=True)

        # Launch Bazel GUI
        msg_gui, err_gui = self.mcap_logic.launch_bazel_with_file(selected_path)
        if msg_gui:
            self.log_message(f"Bazel Bag GUI: {msg_gui}")
        if err_gui:
            self.log_message(f"Bazel Bag GUI: {err_gui}", is_error=True)
        
        # Launch Bazel Viz
        msg_viz, err_viz = self.mcap_logic.launch_bazel_viz()
        if msg_viz:
            self.log_message(f"Bazel Tools Viz: {msg_viz}")
        if err_viz:
            self.log_message(f"Bazel Tools Viz: {err_viz}", is_error=True)

    def open_foxglove_with_browser(self):
        """Open Foxglove in browser"""
        success = self.foxglove_logic.launch_foxglove_browser()
        if success:
            self.log_message("Opened Foxglove in browser.")
        else:
            self.log_message("Failed to open Foxglove in browser.", is_error=True)

    # Subfolder tabs methods (simplified versions)
    def refresh_subfolder_tabs(self, default_folder=None):
        """Refresh subfolder tabs - simplified version"""
        # This is a simplified version - the full implementation would be here
        # For now, just set the current folder if we have one
        if default_folder is None:
            current_path = self.current_subfolder_var.get() or os.path.expanduser('~/data/default')
            default_folder = self.logic.get_effective_default_folder(current_path)
        
        subfolders = self.logic.list_subfolders_in_path(default_folder)
        if len(subfolders) >= 1:
            self.current_mcap_folder_absolute = subfolders[0]

    def on_subfolder_tab_changed(self, event):
        """Handle subfolder tab change - simplified version"""
        # Simplified version
        pass

    # File Explorer methods
    def refresh_explorer(self):
        """Refresh the file explorer"""
        if not self.explorer_file_list:
            return
            
        current_path = self.navigation_logic.get_current_path()
        
        try:
            if not os.path.exists(current_path):
                self.log_message(f"Path does not exist: {current_path}", is_error=True)
                return
            if not os.path.isdir(current_path):
                self.log_message(f"Path is not a directory: {current_path}", is_error=True)
                return
            
            # Update path display
            self.explorer_path_var.set(current_path)
            
            # Get directory contents
            dirs, files = self.file_explorer_logic.list_directory(current_path)
            view_mode = self.explorer_view_mode.get()
            
            # Format for display
            display_items = []
            actual_items = []
            
            # Add parent directory option (unless at root)
            parent_dir = os.path.dirname(current_path)
            if parent_dir != current_path:
                display_items.append("⬆️ .. (Parent Directory)")
                actual_items.append("..")
            
            # Add directories
            for d in dirs:
                display_text = self._format_directory_display(d, view_mode, current_path)
                display_items.append(display_text)
                actual_items.append(d)
            
            # Add files
            for f in files:
                display_text = self._format_file_display(f, view_mode, current_path)
                display_items.append(display_text)
                actual_items.append(f)
            
            # Populate the list
            self.explorer_file_list.files_list = actual_items
            self.explorer_file_list.listbox.delete(0, tk.END)
            for item in display_items:
                self.explorer_file_list.listbox.insert(tk.END, item)
                
        except PermissionError:
            self.log_message(f"Permission denied accessing: {current_path}", is_error=True)
        except Exception as e:
            self.log_message(f"Error refreshing explorer: {e}", is_error=True)

    def _format_directory_display(self, dirname, view_mode, current_path):
        """Format directory display based on view mode"""
        dir_path = os.path.join(current_path, dirname)
        if view_mode == "simple":
            return f"📁 {dirname}"
        elif view_mode == "icons":
            return f"📁\n{dirname[:15]}..." if len(dirname) > 15 else f"📁\n{dirname}"
        else:  # detailed
            try:
                item_count = len([x for x in os.listdir(dir_path) if not x.startswith('.')])
                return f"📁 {dirname:<30} ({item_count} items)"
            except (PermissionError, OSError):
                return f"📁 {dirname:<30} (Access denied)"

    def _format_file_display(self, filename, view_mode, current_path):
        """Format file display based on view mode"""
        file_path = os.path.join(current_path, filename)
        info = self.file_explorer_logic.get_file_info(file_path)
        icon = info['icon']
        
        if view_mode == "simple":
            return f"{icon} {filename}"
        elif view_mode == "icons":
            short_name = filename[:12] + "..." if len(filename) > 15 else filename
            return f"{icon}\n{short_name}"
        else:  # detailed
            import time
            size_str = info['size_str']
            mod_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(info['mtime'])) if info['mtime'] else 'N/A'
            return f"{icon} {filename:<30} {size_str:>10} {mod_str}"

    # Explorer navigation methods
    def go_home_directory(self):
        """Navigate to data directory"""
        home_path = self.navigation_logic.go_home()
        self.refresh_explorer()

    def navigate_to_path(self, event=None):
        """Navigate to the path in the entry field"""
        new_path = self.explorer_path_var.get().strip()
        if self.navigation_logic.navigate_to(new_path):
            self.refresh_explorer()
        else:
            self.log_message(f"Invalid path: {new_path}", is_error=True)
            self.explorer_path_var.set(self.navigation_logic.get_current_path())

    # Explorer event handlers
    def on_explorer_select(self, event):
        """Handle selection change in explorer"""
        if not self.explorer_file_list:
            return
            
        selection = self.explorer_file_list.get_selected_indices()
        current_path = self.navigation_logic.get_current_path()
        
        # Default: all actions disabled
        states = {
            "open_file": False,
            "copy_path": False,  
            "open_foxglove": False,
            "open_bazel": False
        }
        
        if selection:
            idx = selection[0]
            if idx < len(self.explorer_file_list.files_list):
                selected_item = self.explorer_file_list.files_list[idx]
                is_parent_dir = (selected_item == "..")
                
                if not is_parent_dir:
                    item_path = os.path.join(current_path, selected_item)
                    states = self.file_explorer_logic.get_file_action_states(item_path, is_parent_dir)
        
        # Update button states
        if self.explorer_buttons:
            button_state_map = {
                "open_file": tk.NORMAL if states["open_file"] else tk.DISABLED,
                "copy_path": tk.NORMAL if states["copy_path"] else tk.DISABLED,
                "open_foxglove": tk.NORMAL if states["open_with_foxglove"] else tk.DISABLED,
                "open_bazel": tk.NORMAL if states["open_with_bazel"] else tk.DISABLED,
                "open_multiple": tk.DISABLED  # Will be enabled based on multiple selection logic
            }
            self.explorer_buttons.set_all_button_states(button_state_map)

    def on_explorer_double_click(self, event):
        """Handle double-click on explorer items"""
        self.explorer_navigate_selected()

    def on_explorer_enter_key(self, event):
        """Handle Enter key in explorer"""
        self.explorer_navigate_selected()

    def on_explorer_backspace_key(self, event):
        """Handle Backspace key in explorer"""
        if self.navigation_logic.can_go_up():
            self.navigation_logic.go_up()
            self.refresh_explorer()

    def explorer_navigate_selected(self):
        """Navigate into directory or open file"""
        if not self.explorer_file_list:
            return
            
        selection = self.explorer_file_list.get_selected_indices()
        if not selection:
            return
            
        idx = selection[0]
        if idx >= len(self.explorer_file_list.files_list):
            return
            
        selected_item = self.explorer_file_list.files_list[idx]
        current_path = self.navigation_logic.get_current_path()
        
        if selected_item == "..":
            if self.navigation_logic.can_go_up():
                self.navigation_logic.go_up()
                self.refresh_explorer()
        else:
            item_path = os.path.join(current_path, selected_item)
            if os.path.isdir(item_path):
                if self.navigation_logic.navigate_to(item_path):
                    self.refresh_explorer()
            else:
                self.open_file(item_path)

    # File operations
    def open_selected_file(self):
        """Open the currently selected file"""
        if not self.explorer_file_list:
            return
            
        selection = self.explorer_file_list.get_selected_indices()
        if not selection:
            return
            
        idx = selection[0]
        if idx >= len(self.explorer_file_list.files_list):
            return
            
        selected_item = self.explorer_file_list.files_list[idx]
        if selected_item != "..":
            current_path = self.navigation_logic.get_current_path()
            item_path = os.path.join(current_path, selected_item)
            if os.path.isfile(item_path):
                self.open_file(item_path)

    def open_file(self, file_path):
        """Open a file using the system default application"""
        success, msg = self.file_explorer_logic.open_file(file_path)
        if success:
            self.log_message(msg)
        else:
            self.log_message(msg, is_error=True)

    def open_in_file_manager(self):
        """Open current directory in system file manager"""
        current_path = self.navigation_logic.get_current_path()
        success, msg = self.file_explorer_logic.open_in_file_manager(current_path)
        if success:
            self.log_message(msg)
        else:
            self.log_message(msg, is_error=True)

    def copy_selected_path(self):
        """Copy the path of the selected item to clipboard"""
        if not self.explorer_file_list:
            return
            
        selection = self.explorer_file_list.get_selected_indices()
        if not selection:
            return
            
        idx = selection[0]
        if idx >= len(self.explorer_file_list.files_list):
            return
            
        selected_item = self.explorer_file_list.files_list[idx]
        if selected_item != "..":
            current_path = self.navigation_logic.get_current_path()
            item_path = os.path.join(current_path, selected_item)
            success, msg = self.file_explorer_logic.copy_to_clipboard(self.root, item_path)
            if success:
                self.log_message(msg)
            else:
                self.log_message(msg, is_error=True)

    def open_with_foxglove(self):
        """Open the selected MCAP file with Foxglove"""
        selected_mcap_path = self._get_selected_explorer_mcap_path()
        if selected_mcap_path:
            self.log_message(f"Launching Foxglove with {os.path.basename(selected_mcap_path)}...")
            message, error = self.foxglove_logic.launch_foxglove_with_file(selected_mcap_path)
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
        else:
            self.log_message("Selected file is not an MCAP file.", is_error=True)

    def open_with_bazel(self):
        """Open the selected MCAP file with Bazel Bag GUI"""
        selected_mcap_path = self._get_selected_explorer_mcap_path()
        if selected_mcap_path:
            self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(selected_mcap_path)}...")
            message, error = self.mcap_logic.launch_bazel_with_file(selected_mcap_path)
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
        else:
            self.log_message("Selected file is not an MCAP file.", is_error=True)

    def open_multiple_with_bazel(self):
        """Open multiple selected MCAP files with Bazel Bag GUI using symlinks"""
        mcap_files = self._get_selected_explorer_mcap_paths()
        
        if len(mcap_files) > 1:
            self.log_message(f"Launching Bazel Bag GUI with {len(mcap_files)} selected MCAP files using symlinks...")
            message, error, symlink_dir = self.mcap_logic.launch_bazel_with_multiple_files(mcap_files)
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
        elif len(mcap_files) == 1:
            # Fall back to single file launch
            self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(mcap_files[0])}...")
            message, error = self.mcap_logic.launch_bazel_with_file(mcap_files[0])
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
        else:
            self.log_message("No MCAP files selected.", is_error=True)

    def _get_selected_explorer_mcap_path(self):
        """Get the first selected MCAP file path in explorer"""
        if not self.explorer_file_list:
            return None
            
        selection = self.explorer_file_list.get_selected_indices()
        if not selection:
            return None
            
        idx = selection[0]
        if idx >= len(self.explorer_file_list.files_list):
            return None
            
        selected_item = self.explorer_file_list.files_list[idx]
        if selected_item == "..":
            return None
            
        current_path = self.navigation_logic.get_current_path()
        item_path = os.path.join(current_path, selected_item)
        
        if os.path.isfile(item_path) and self.file_explorer_logic.is_mcap_file(item_path):
            return item_path
        
        return None

    def _get_selected_explorer_mcap_paths(self):
        """Get paths of all selected MCAP files in the explorer"""
        if not self.explorer_file_list:
            return []
            
        selection = self.explorer_file_list.get_selected_indices()
        mcap_paths = []
        current_path = self.navigation_logic.get_current_path()
        
        for idx in selection:
            if idx < len(self.explorer_file_list.files_list):
                selected_item = self.explorer_file_list.files_list[idx]
                if selected_item != "..":
                    item_path = os.path.join(current_path, selected_item)
                    if os.path.isfile(item_path) and self.file_explorer_logic.is_mcap_file(item_path):
                        mcap_paths.append(item_path)
        
        return mcap_paths

    # Cleanup methods  
    def on_closing(self):
        """Handle application closing"""
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
