import tkinter as tk
from tkinter import ttk
import os
import json
from typing import Optional, Callable

class SettingsTab:
    settings_config = [
        {
            'label': 'Bazel Working Directory:',
            'key': 'bazel_working_dir',
            'type': 'str',
            'widget': 'entry',
            'width': 60
        },
        {
            'label': 'Bazel Tools Viz Command:',
            'key': 'bazel_tools_viz_cmd',
            'type': 'str',
            'widget': 'entry',
            'width': 60
        },
        {
            'label': 'Bazel Bag GUI Command:',
            'key': 'bazel_bag_gui_cmd',
            'type': 'str',
            'widget': 'entry',
            'width': 60
        },
                {
            'label': 'NAS Directory:',
            'key': 'nas_dir',
            'type': 'str',
            'widget': 'entry',
            'width': 60
        },
        {
            'label': 'Open Foxglove in browser',
            'key': 'open_foxglove_in_browser',
            'type': 'bool',
            'widget': 'checkbutton',
        },
    ]

    def __init__(self, parent, logic, log_message):
        self.frame = ttk.Frame(parent)
        self.logic = logic
        self.log_message = log_message
        self.vars = {}
        self.entries = {}
        self.settings_path = os.path.expanduser('~/.foxglove_gui_settings.json')
        self.settings = self.load_settings()
        self.on_nas_dir_changed: Optional[Callable[[str], None]] = None
        self.create_widgets()

    def load_settings(self):
        """
        Loads settings from a JSON file, or returns defaults if not found.
        """
        default_settings = {
            'bazel_tools_viz_cmd': 'bazel run //tools/viz',
            'bazel_bag_gui_cmd': 'bazel run //tools/bag:gui',
            'bazel_working_dir': os.path.expanduser('~/av-system/catkin_ws/src'),
            'nas_dir': '',
            'open_foxglove_in_browser': True,
        }
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    user_settings = json.load(f)
                # Merge defaults with user settings, ensuring all keys are present
                settings = default_settings.copy()
                settings.update(user_settings)
                return settings
            except Exception as e:
                self.log_message(f"Error loading settings, using defaults: {e}", is_error=True)
                return default_settings
        return default_settings

    def save_settings(self, settings_dict=None):
        """
        Saves provided settings to the JSON file.
        """
        try:
            if settings_dict is not None:
                self.settings.update(settings_dict)
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
            return True, None
        except Exception as e:
            return False, str(e)

    def reset_settings(self):
        """Resets settings to their default values and saves them."""
        default_settings = {
            'bazel_tools_viz_cmd': 'bazel run //tools/viz',
            'bazel_bag_gui_cmd': 'bazel run //tools/bag:gui',
            'bazel_working_dir': os.path.expanduser('~/av-system/catkin_ws/src'),
            'nas_dir': '',
            'open_foxglove_in_browser': True,
        }
        self.settings = default_settings.copy()
        self.save_settings(self.settings)

    def get_setting(self, key):
        """Gets a specific setting value by key."""
        return self.settings.get(key)

    def create_widgets(self):
        settings_frame = ttk.LabelFrame(self.frame, text="Configuration")
        settings_frame.pack(fill="x", padx=10, pady=10)

        row = 0
        for config in self.settings_config:
            key = config['key']
            value = self.get_setting(key)
            if config['type'] == 'bool':
                var = tk.BooleanVar(value=value if value is not None else True)
                widget = ttk.Checkbutton(settings_frame, text=config['label'], variable=var)
                widget.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)
                self.entries[key] = widget
            else:
                var = tk.StringVar(value=value)
                ttk.Label(settings_frame, text=config['label']).grid(row=row, column=0, sticky="w", padx=5, pady=2)
                entry = ttk.Entry(settings_frame, textvariable=var, width=config.get('width', 40))
                entry.grid(row=row, column=1, sticky="we", padx=5, pady=2)
                self.entries[key] = entry
            self.vars[key] = var
            row += 1

        settings_frame.columnconfigure(1, weight=1)

        # Buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        self.save_button = ttk.Button(button_frame, text="Save Settings", command=self.save_settings_button)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.reset_button = ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_settings_button)
        self.reset_button.pack(side=tk.LEFT, padx=5)

    def save_settings_button(self):
        settings = {}
        for config in self.settings_config:
            key = config['key']
            var = self.vars[key]
            if config['type'] == 'bool':
                settings[key] = var.get()
            else:
                settings[key] = var.get()
        old_nas_dir = self.settings.get('nas_dir')
        new_nas_dir = settings.get('nas_dir')
        self.save_settings(settings)
        if self.on_nas_dir_changed and new_nas_dir != old_nas_dir and isinstance(new_nas_dir, str) and new_nas_dir:
            self.on_nas_dir_changed(new_nas_dir)
        self.log_message("Settings saved successfully.")

    def reset_settings_button(self):
        self.reset_settings()
        for config in self.settings_config:
            key = config['key']
            value = self.get_setting(key)
            if config['type'] == 'bool':
                self.vars[key].set(value if value is not None else True)
            else:
                self.vars[key].set(value)
        self.log_message("Settings reset to defaults.")

    def get_entry_widgets(self):
        # Return only entry widgets (not checkbuttons)
        return tuple(
            self.entries[config['key']]
            for config in self.settings_config
            if config['widget'] == 'entry'
        )
