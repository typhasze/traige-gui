import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Listbox, Scrollbar, Frame, Label, Entry, Button, Text, END, SINGLE, VERTICAL, HORIZONTAL
import os
import signal
import webbrowser
import shutil

# Import modular components
from logic.foxglove_logic import FoxgloveLogic
from logic.mcap_logic import McapLogic
from logic.file_explorer_logic import FileExplorerLogic
from logic.navigation_logic import NavigationLogic
from gui.logging_component import LoggingComponent
from gui.components.foxglove_tab import FoxgloveTab
from gui.components.explorer_tab import ExplorerTab

class ModularFoxgloveAppGUIManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Foxglove MCAP Launcher")
        
        # Initialize modular components
        self.foxglove_logic = FoxgloveLogic()
        self.mcap_logic = McapLogic()
        self.file_explorer_logic = FileExplorerLogic()
        self.navigation_logic = NavigationLogic()
        self.logging_component = LoggingComponent()
        
        # Application state
        self.current_mcap_folder_absolute = None
        self.mcap_filename_from_link = None
        self.mcap_files_list = []
        
        # File explorer state
        self.current_explorer_path = os.path.expanduser("~/data")
        self.explorer_files_list = []
        self.explorer_view_mode = tk.StringVar(value="detailed")
        
        self.create_widgets()
        self.setup_signal_handlers()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.minsize(800, 600)

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create main tab system
        self.main_notebook = ttk.Notebook(main_frame)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs using modular components
        self.foxglove_tab = FoxgloveTab(
            self.main_notebook, 
            self.foxglove_logic, 
            self.mcap_logic,
            self.log_message
        )
        self.main_notebook.add(self.foxglove_tab.frame, text="Foxglove MCAP")
        
        self.explorer_tab = ExplorerTab(
            self.main_notebook,
            self.file_explorer_logic,
            self.navigation_logic,
            self.foxglove_logic,
            self.current_explorer_path,
            self.explorer_view_mode,
            self.log_message
        )
        self.main_notebook.add(self.explorer_tab.frame, text="File Explorer")
        
        # Set up shared logging frame
        self.create_shared_log_frame(main_frame)

    def create_shared_log_frame(self, parent_frame):
        """Create the shared logging frame"""
        status_frame = ttk.LabelFrame(parent_frame, text="Log", padding="10")
        status_frame.pack(padx=5, pady=5, fill="both", expand=True)
        
        # Use the logging component
        self.logging_component.create_log_widget(status_frame)
        self.status_text = self.logging_component.log_widget

    def log_message(self, message, is_error=False, clear_first=False):
        """Delegate logging to the logging component"""
        self.logging_component.log_message(message, is_error, clear_first)

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
        termination_log = self.foxglove_logic.terminate_all_processes()
        self.log_message(termination_log)
        self.root.destroy()

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        import sys
        def handler(signum, frame):
            self.on_closing()
            sys.exit(0)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
