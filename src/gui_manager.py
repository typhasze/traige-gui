import tkinter as tk
from tkinter import ttk, filedialog
import os
import signal
import sys
import shutil
from .core_logic import FoxgloveAppLogic
from .logic.file_explorer_logic import FileExplorerLogic
from .ui.components.file_explorer_tab import FileExplorerTab
from .ui.components.foxglove_tab import FoxgloveTab
from .ui.components.settings_tab import SettingsTab

class FoxgloveAppGUIManager:
    def __init__(self, root):
        self.root = root
        self.logic = FoxgloveAppLogic(log_callback=self.log_message)
        self.file_explorer_logic = FileExplorerLogic()

        # --- Main UI Frames ---
        self.root.title("Foxglove MCAP Launcher")
        self.root.geometry("1200x800") # Set a default size
        self.root.minsize(800, 600) # Set minimum size

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        self.main_notebook = ttk.Notebook(main_frame)
        self.main_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create the button map and action buttons first
        self._button_map = {}
        self.create_shared_action_buttons(main_frame)

        # Now, create the tabs that might use the buttons during initialization
        self.file_explorer_tab = FileExplorerTab(self.main_notebook, self.root, self.logic, self.file_explorer_logic, self.log_message, self._update_button_states)
        self.foxglove_tab = FoxgloveTab(self.main_notebook, self.root, self.logic, self.log_message, self.disable_file_specific_action_buttons, self.enable_file_specific_action_buttons)
        self.settings_tab = SettingsTab(self.main_notebook, self.logic, self.log_message)

        self.main_notebook.add(self.file_explorer_tab.frame, text="File Explorer")
        self.main_notebook.add(self.foxglove_tab.frame, text="Foxglove MCAP")
        self.main_notebook.add(self.settings_tab.frame, text="Settings")

        # --- Shared Components ---
        self.create_shared_log_frame(main_frame)
        # self._create_action_buttons(main_frame) # This line is moved up

        # --- Initial State ---
        self._cache_tab_indices()
        self.on_tab_changed() # Set initial button states
        self.setup_signal_handlers()
        
        # Bind tab change event
        self.main_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # Bind Escape key to clear selections
        self.root.bind("<Escape>", self.clear_all_selections)

    def create_shared_action_buttons(self, parent_frame):
        """Creates the action buttons that are shared across tabs"""
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=5)

        # --- Button Definitions ---
        self.open_file_button = self._create_button(button_frame, "Open File", self.open_selected_file)
        self.copy_path_button = self._create_button(button_frame, "Copy Path", self.copy_selected_path)
        self.open_in_manager_button = self._create_button(button_frame, "Open in File Manager", self.open_in_file_manager)
        self.open_foxglove_button = self._create_button(button_frame, "Open with Foxglove", self.open_with_foxglove)
        self.open_bazel_button = self._create_button(button_frame, "Open with Bazel GUI", self.open_with_bazel)
        self.launch_bazel_viz_button = self._create_button(button_frame, "Launch Bazel Tools Viz", self.launch_bazel_viz)

        # --- Button Map for State Management ---
        self._button_map = {
            "open_file": self.open_file_button,
            "copy_path": self.copy_path_button,
            "open_with_foxglove": self.open_foxglove_button,
            "open_with_bazel": self.open_bazel_button,
        }

    def create_shared_log_frame(self, parent_frame):
        # --- Status/Log Frame ---
        status_frame = ttk.LabelFrame(parent_frame, text="Log", padding="10")
        status_frame.pack(padx=5, pady=5, fill="both", expand=True)
        
        log_container = ttk.Frame(status_frame)
        log_container.pack(fill="both", expand=True)

        log_yscrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL)
        log_xscrollbar = ttk.Scrollbar(log_container, orient=tk.HORIZONTAL)
        
        self.log_text = tk.Text(log_container, height=6, wrap=tk.WORD, yscrollcommand=log_yscrollbar.set, state=tk.DISABLED)
        log_yscrollbar.config(command=self.log_text.yview)
        log_xscrollbar.config(command=self.log_text.xview)
        
        log_yscrollbar.pack(side="right", fill="y")
        log_xscrollbar.pack(side="bottom", fill="x")
        self.log_text.pack(side="left", fill="both", expand=True)

    def log_message(self, message, is_error=False, clear_first=False):
        self.log_text.config(state=tk.NORMAL)
        if clear_first:
            self.log_text.delete('1.0', tk.END)
        
        tag = "error" if is_error else "info"
        prefix = "ERROR: " if is_error else "INFO: "
        
        # Split message by newlines to apply tags correctly if needed
        for line in message.splitlines():
            self.log_text.insert(tk.END, f"{prefix}{line}\n", tag)
            
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()

    def enable_file_specific_action_buttons(self):
        states = {"open_with_foxglove": True, "open_with_bazel": True}
        self._update_button_states(states)

    def disable_file_specific_action_buttons(self):
        states = {"open_with_foxglove": False, "open_with_bazel": False}
        self._update_button_states(states)

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
        def handler(signum, frame):
            self.on_closing()
            sys.exit(0)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def _create_button(self, parent, text, command, state=tk.DISABLED, **pack_opts):
        """Helper to create and pack a ttk.Button with common options."""
        btn = ttk.Button(parent, text=text, command=command, state=state)
        btn.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x", **pack_opts)
        return btn

    # --- Cross-Tab Action Methods ---

    def open_selected_file(self):
        """Open the currently selected file in the explorer tab."""
        if self.main_notebook.index(self.main_notebook.select()) == self._explorer_tab_index:
            self.file_explorer_tab.open_selected_file()

    def open_in_file_manager(self):
        """Open current directory in system file manager via FileExplorerLogic"""
        current_tab = self.main_notebook.index(self.main_notebook.select())
        if current_tab == self._foxglove_tab_index:
            folder_to_open = self.foxglove_tab.current_mcap_folder_absolute
        else:
            folder_to_open = self.file_explorer_tab.current_explorer_path
        
        if folder_to_open and os.path.isdir(folder_to_open):
            success, msg = self.file_explorer_logic.open_in_file_manager(folder_to_open)
            if success:
                self.log_message(msg)
            else:
                self.log_message(msg, is_error=True)
        else:
            self.log_message(f"Folder does not exist: {folder_to_open}", is_error=True)

    def copy_selected_path(self):
        """Copy the path of the selected item in the explorer tab to clipboard."""
        if self.main_notebook.index(self.main_notebook.select()) == self._explorer_tab_index:
            selection = self.file_explorer_tab.explorer_listbox.curselection()
            if selection:
                idx = selection[0]
                if idx < len(self.file_explorer_tab.explorer_files_list):
                    selected_item = self.file_explorer_tab.explorer_files_list[idx]
                    if selected_item != "..":
                        item_path = os.path.join(self.file_explorer_tab.current_explorer_path, selected_item)
                        success, msg = self.file_explorer_logic.copy_to_clipboard(self.root, item_path)
                        if success:
                            self.log_message(msg)
                        else:
                            self.log_message(msg, is_error=True)

    def open_with_foxglove(self):
        """Open the selected MCAP file with Foxglove from either tab."""
        current_tab = self.main_notebook.index(self.main_notebook.select())
        
        file_path = None
        if current_tab == self._explorer_tab_index:
            mcap_files = self.file_explorer_tab.get_selected_explorer_mcap_paths()
            if not mcap_files:
                self.log_message("No MCAP file selected in File Explorer.", is_error=True)
                return
            file_path = mcap_files[-1]
        elif current_tab == self._foxglove_tab_index:
            file_path = self.foxglove_tab.get_selected_mcap_path()
            if not file_path:
                self.log_message("No MCAP file selected in Foxglove MCAP tab.", is_error=True)
                return
        
        if file_path:
            self.log_message(f"Launching Foxglove with {os.path.basename(file_path)}...")
            message, error = self.logic.launch_foxglove(file_path)
            if message:
                self.log_message(message)
            if error:
                self.log_message(error, is_error=True)
        else:
            # This case handles if the button is visible on a tab where it shouldn't be.
            self.log_message("Open with Foxglove is not available for the current selection.", is_error=True)


    def open_with_bazel(self):
        """Open the selected MCAP file(s) with Bazel Bag GUI from either tab."""
        current_tab = self.main_notebook.index(self.main_notebook.select())
        
        mcap_files = []
        if current_tab == self._explorer_tab_index:
            mcap_files = self.file_explorer_tab.get_selected_explorer_mcap_paths()
            if not mcap_files:
                self.log_message("No MCAP file selected in File Explorer.", is_error=True)
                return
        elif current_tab == self._foxglove_tab_index:
            mcap_files = self.foxglove_tab.get_selected_mcap_paths()
            if not mcap_files:
                self.log_message("No MCAP file selected in Foxglove MCAP tab.", is_error=True)
                return

        if not mcap_files:
             self.log_message("Open with Bazel is not available for the current selection.", is_error=True)
             return

        if len(mcap_files) == 1:
            self.log_message(f"Launching Bazel Bag GUI with {os.path.basename(mcap_files[0])}...")
            message, error = self.logic.launch_bazel_bag_gui(mcap_files[0])
            if message: self.log_message(message)
            if error: self.log_message(error, is_error=True)
        else:
            self.log_message(f"Launching Bazel Bag GUI with {len(mcap_files)} selected MCAP files using symlinks...")
            message, error, symlink_dir = self.logic.play_bazel_bag_gui_with_symlinks(mcap_files)
            if message: self.log_message(message)
            if error: self.log_message(error, is_error=True)

    def on_tab_changed(self, event=None):
        """Update file action button states when switching tabs."""
        current_tab_index = self.main_notebook.index(self.main_notebook.select())
        
        # Disable all buttons first
        self._update_button_states({key: False for key in self._button_map})
        self.open_in_manager_button.config(state=tk.NORMAL) # This is always available
        self.launch_bazel_viz_button.config(state=tk.NORMAL) # This is always available

        if current_tab_index == self._explorer_tab_index:
            # File Explorer tab: update based on explorer selection (suppress logging to avoid spam)
            self.file_explorer_tab.on_explorer_select(None, suppress_log=True)
        elif current_tab_index == self._foxglove_tab_index:
            # Foxglove MCAP tab: update based on MCAP list selection
            self.foxglove_tab.on_file_select(None, suppress_log=True)
        else:
            # Settings or other tabs: disable all file-specific action buttons
            self.disable_file_specific_action_buttons()

    def _cache_tab_indices(self):
        """Cache tab indices for performance optimization"""
        self._explorer_tab_index = 0
        self._foxglove_tab_index = 1
        self._settings_tab_index = 2

    def _update_button_states(self, states):
        """Efficiently update multiple button states in one batch"""
        state_map = {True: tk.NORMAL, False: tk.DISABLED}
        updates = []
        
        for state_key, button in self._button_map.items():
            new_state = state_map[states.get(state_key, False)]
            if button['state'] != new_state:
                updates.append((button, new_state))
        
        # Batch update all buttons that need changing
        for button, new_state in updates:
            button.config(state=new_state)

    def clear_all_selections(self, event=None):
        """Clear text selections from all entry widgets"""
        entry_widgets = (
            self.file_explorer_tab.explorer_path_entry, 
            self.foxglove_tab.link_entry,
        )
        
        for widget in entry_widgets:
            if hasattr(widget, 'selection_clear'):
                widget.selection_clear()
        
        for widget in self.settings_tab.get_entry_widgets():
            if hasattr(widget, 'selection_clear'):
                widget.selection_clear()