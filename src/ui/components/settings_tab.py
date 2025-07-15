import tkinter as tk
from tkinter import ttk

class SettingsTab:
    def __init__(self, parent, logic, log_message):
        self.frame = ttk.Frame(parent)
        self.logic = logic
        self.log_message = log_message

        # UI Widgets
        self.create_widgets()

    def create_widgets(self):
        settings_frame = ttk.LabelFrame(self.frame, text="Configuration")
        settings_frame.pack(fill="x", padx=10, pady=10)

        # Bazel working directory
        self.bazel_working_dir_var = tk.StringVar(value=self.logic.get_setting('bazel_working_dir'))
        ttk.Label(settings_frame, text="Bazel Working Directory:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.bazel_working_dir_entry = ttk.Entry(settings_frame, textvariable=self.bazel_working_dir_var, width=60)
        self.bazel_working_dir_entry.grid(row=0, column=1, sticky="we", padx=5, pady=2)

        # Bazel tools viz command
        self.bazel_tools_viz_var = tk.StringVar(value=self.logic.get_setting('bazel_tools_viz_cmd'))
        ttk.Label(settings_frame, text="Bazel Tools Viz Command:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.bazel_tools_viz_entry = ttk.Entry(settings_frame, textvariable=self.bazel_tools_viz_var, width=60)
        self.bazel_tools_viz_entry.grid(row=1, column=1, sticky="we", padx=5, pady=2)

        # Bazel bag GUI command
        self.bazel_bag_gui_var = tk.StringVar(value=self.logic.get_setting('bazel_bag_gui_cmd'))
        ttk.Label(settings_frame, text="Bazel Bag GUI Command:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.bazel_bag_gui_entry = ttk.Entry(settings_frame, textvariable=self.bazel_bag_gui_var, width=60)
        self.bazel_bag_gui_entry.grid(row=2, column=1, sticky="we", padx=5, pady=2)

        # Foxglove open preference
        self.foxglove_in_browser_var = tk.BooleanVar(value=self.logic.get_setting('open_foxglove_in_browser') or True)
        self.foxglove_in_browser_check = ttk.Checkbutton(settings_frame, text="Open Foxglove in browser", variable=self.foxglove_in_browser_var)
        self.foxglove_in_browser_check.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        settings_frame.columnconfigure(1, weight=1)

        # Buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        self.save_button = ttk.Button(button_frame, text="Save Settings", command=self.save_settings)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.reset_button = ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_settings)
        self.reset_button.pack(side=tk.LEFT, padx=5)

    def save_settings(self):
        settings = {
            'bazel_working_dir': self.bazel_working_dir_var.get(),
            'bazel_tools_viz_cmd': self.bazel_tools_viz_var.get(),
            'bazel_bag_gui_cmd': self.bazel_bag_gui_var.get(),
            'open_foxglove_in_browser': self.foxglove_in_browser_var.get()
        }
        self.logic.save_settings(settings)
        self.log_message("Settings saved successfully.")

    def reset_settings(self):
        self.logic.reset_settings()
        self.bazel_working_dir_var.set(self.logic.get_setting('bazel_working_dir'))
        self.bazel_tools_viz_var.set(self.logic.get_setting('bazel_tools_viz_cmd'))
        self.bazel_bag_gui_var.set(self.logic.get_setting('bazel_bag_gui_cmd'))
        self.foxglove_in_browser_var.set(self.logic.get_setting('open_foxglove_in_browser') or True)
        self.log_message("Settings reset to defaults.")

    def get_entry_widgets(self):
        return (
            self.bazel_working_dir_entry,
            self.bazel_tools_viz_entry,
            self.bazel_bag_gui_entry
        )
