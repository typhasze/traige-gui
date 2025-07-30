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
            'label': 'Backup NAS Directory:',
            'key': 'backup_nas_dir',
            'type': 'str',
            'widget': 'entry',
            'width': 60
        },
        {
            'label': 'Max MCAP Files for Foxglove:',
            'key': 'max_foxglove_files',
            'type': 'int',
            'widget': 'entry',
            'width': 20
        },
        {
            'label': 'Bazel Bag GUI Rate:',
            'key': 'bazel_bag_gui_rate',
            'type': 'float',
            'widget': 'entry',
            'width': 20
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
        # Initialize logic with settings after loading them
        self.logic.update_search_paths(self.settings.get('nas_dir'), self.settings.get('backup_nas_dir'))

    def load_settings(self):
        """
        Loads settings from a JSON file, or returns defaults if not found.
        Improved error handling and structure validation.
        """
        default_settings = {
            'bazel_tools_viz_cmd': 'bazel run //tools/viz',
            'bazel_bag_gui_cmd': 'bazel run //tools/bag:gui',
            'bazel_working_dir': os.path.expanduser('~/av-system/catkin_ws/src'),
            'nas_dir': os.path.expanduser('~/data'),
            'backup_nas_dir': os.path.expanduser('~/data/psa_logs_backup_nas3'),
            'max_foxglove_files': 50,  # Reasonable default limit for performance
            'bazel_bag_gui_rate': 1.0,  # Default playback rate for Bazel Bag GUI
            'open_foxglove_in_browser': True,
        }
        
        if not os.path.exists(self.settings_path):
            return default_settings
            
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
                
            # Validate that user_settings is a dictionary
            if not isinstance(user_settings, dict):
                self.log_message("Settings file corrupted, using defaults", is_error=True)
                return default_settings
                
            # Merge defaults with user settings, ensuring all keys are present
            settings = default_settings.copy()
            settings.update(user_settings)
            return settings
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.log_message(f"Error parsing settings file, using defaults: {e}", is_error=True)
            return default_settings
        except (IOError, OSError) as e:
            self.log_message(f"Error reading settings file, using defaults: {e}", is_error=True)
            return default_settings

    def save_settings(self, settings_dict=None):
        """
        Saves provided settings to the JSON file.
        Improved error handling and atomic writes.
        """
        try:
            if settings_dict is not None:
                self.settings.update(settings_dict)
                
            # Use atomic write to prevent corruption
            temp_path = self.settings_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            
            # Atomic rename on Unix systems
            os.replace(temp_path, self.settings_path)
            
            # After saving, update the logic instance
            self.logic.update_search_paths(
                self.settings.get('nas_dir'), 
                self.settings.get('backup_nas_dir')
            )
            return True, None
            
        except (IOError, OSError) as e:
            return False, f"File error: {e}"
        except (TypeError, ValueError) as e:
            return False, f"Data error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def reset_settings(self):
        """Resets settings to their default values and saves them."""
        default_settings = {
            'bazel_tools_viz_cmd': 'bazel run //tools/viz',
            'bazel_bag_gui_cmd': 'bazel run //tools/bag:gui',
            'bazel_working_dir': os.path.expanduser('~/av-system/catkin_ws/src'),
            'nas_dir': os.path.expanduser('~/data'),
            'backup_nas_dir': os.path.expanduser('~/data/psa_logs_backup_nas3'),
            'max_foxglove_files': 50,  # Reasonable default limit for performance
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
                # Handle string, integer, and float types
                if config['type'] in ['int', 'float']:
                    var = tk.StringVar(value=str(value) if value is not None else "")
                else:
                    var = tk.StringVar(value=value if value is not None else "")
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
        old_nas_dir = self.settings.get('nas_dir')
        
        new_settings = {}
        for config in self.settings_config:
            key = config['key']
            var = self.vars[key]
            if config['type'] == 'bool':
                new_settings[key] = var.get()
            elif config['type'] == 'int':
                try:
                    new_settings[key] = int(var.get())
                except ValueError:
                    # Use default value if invalid integer
                    new_settings[key] = 50 if key == 'max_foxglove_files' else 0
                    self.log_message(f"Invalid integer for {config['label']}, using default.", is_error=True)
            elif config['type'] == 'float':
                try:
                    new_settings[key] = float(var.get())
                except ValueError:
                    # Use default value if invalid float
                    new_settings[key] = 1.0 if key == 'bazel_bag_gui_rate' else 0.0
                    self.log_message(f"Invalid number for {config['label']}, using default.", is_error=True)
            else:
                new_settings[key] = var.get()

        # Save the new settings
        self.save_settings(new_settings)
        
        # Now that self.settings is updated, get the new_nas_dir
        new_nas_dir = self.settings.get('nas_dir')

        # Check if the nas_dir has changed and trigger the callback
        if self.on_nas_dir_changed and new_nas_dir != old_nas_dir:
            if isinstance(new_nas_dir, str) and new_nas_dir:
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
