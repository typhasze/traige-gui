import json
import os
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ...utils.constants import DEFAULT_SETTINGS, SETTINGS_FILE_PATH


class SettingsTab:
    settings_config = [
        {
            "label": "Bazel Working Directory:",
            "key": "bazel_working_dir",
            "type": "str",
            "widget": "entry",
            "width": 60,
        },
        {
            "label": "Bazel Tools Viz Command:",
            "key": "bazel_tools_viz_cmd",
            "type": "str",
            "widget": "entry",
            "width": 60,
        },
        {"label": "Bazel Bag GUI Command:", "key": "bazel_bag_gui_cmd", "type": "str", "widget": "entry", "width": 60},
        {"label": "NAS Directory:", "key": "nas_dir", "type": "str", "widget": "entry", "width": 60},
        {"label": "Backup NAS Directory:", "key": "backup_nas_dir", "type": "str", "widget": "entry", "width": 60},
        {"label": "LOGGING Directory:", "key": "logging_dir", "type": "str", "widget": "entry", "width": 60},
        {
            "label": "Max MCAP Files for Foxglove:",
            "key": "max_foxglove_files",
            "type": "int",
            "widget": "entry",
            "width": 20,
        },
        {"label": "Bazel Bag GUI Rate:", "key": "bazel_bag_gui_rate", "type": "float", "widget": "entry", "width": 20},
        {
            "label": "Open Foxglove in browser",
            "key": "open_foxglove_in_browser",
            "type": "bool",
            "widget": "checkbutton",
        },
        {
            "label": "Single instance for Video",
            "key": "single_instance_video",
            "type": "bool",
            "widget": "checkbutton",
        },
        {
            "label": "Single instance for Rosbag",
            "key": "single_instance_rosbag",
            "type": "bool",
            "widget": "checkbutton",
        },
        {
            "label": "Auto-open event log for TG folders",
            "key": "auto_open_event_log_for_tg",
            "type": "bool",
            "widget": "checkbutton",
        },
        {
            "label": "Open event log viewer as tab",
            "key": "event_log_viewer_as_tab",
            "type": "bool",
            "widget": "checkbutton",
        },
    ]

    def __init__(self, parent, logic, log_message):
        self.frame = ttk.Frame(parent)
        self.logic = logic
        self.log_message = log_message
        self.vars = {}
        self.entries = {}
        self.settings_path = SETTINGS_FILE_PATH
        self.settings = self.load_settings()
        if hasattr(self.logic, "set_runtime_settings"):
            self.logic.set_runtime_settings(self.settings)
        self.on_nas_dir_changed: Optional[Callable[[str], None]] = None
        self.on_logging_dir_changed: Optional[Callable[[str], None]] = None
        self.create_widgets()
        # Initialize logic with settings after loading them
        self.logic.update_search_paths(self.settings.get("nas_dir"), self.settings.get("backup_nas_dir"))

    def load_settings(self):
        """Load settings from file or return defaults."""
        if not os.path.exists(self.settings_path):
            return DEFAULT_SETTINGS.copy()

        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                user_settings = json.load(f)

            # Validate that user_settings is a dictionary
            if not isinstance(user_settings, dict):
                self.log_message("Settings file corrupted, using defaults", is_error=True)
                return DEFAULT_SETTINGS.copy()

            settings = DEFAULT_SETTINGS.copy()
            settings.update(user_settings)
            return settings

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.log_message(f"Error parsing settings file, using defaults: {e}", is_error=True)
            return DEFAULT_SETTINGS.copy()
        except (IOError, OSError) as e:
            self.log_message(f"Error reading settings file, using defaults: {e}", is_error=True)
            return DEFAULT_SETTINGS.copy()

    def save_settings(self, settings_dict=None):
        try:
            if settings_dict is not None:
                self.settings.update(settings_dict)

            temp_path = self.settings_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)

            os.replace(temp_path, self.settings_path)

            self.logic.update_search_paths(self.settings.get("nas_dir"), self.settings.get("backup_nas_dir"))
            return True, None

        except (IOError, OSError) as e:
            return False, f"File error: {e}"
        except (TypeError, ValueError) as e:
            return False, f"Data error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def reset_settings(self):
        """Reset settings to defaults."""
        self.settings = DEFAULT_SETTINGS.copy()
        self.save_settings(self.settings)

    def get_setting(self, key):
        return self.settings.get(key)

    def create_widgets(self):
        settings_frame = ttk.LabelFrame(self.frame, text="Configuration")
        settings_frame.pack(fill="x", padx=10, pady=10)

        row = 0
        checkbox_col = 0  # Track column position for checkboxes
        max_checkbox_cols = 3  # Maximum checkboxes per row
        checkbox_row_frame = None

        for config in self.settings_config:
            key = config["key"]
            value = self.get_setting(key)
            if config["type"] == "bool":
                if checkbox_col == 0:
                    checkbox_row_frame = ttk.Frame(settings_frame)
                    checkbox_row_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)

                var = tk.BooleanVar(value=value if value is not None else True)
                widget = ttk.Checkbutton(
                    checkbox_row_frame,
                    text=config["label"],
                    variable=var,
                    command=lambda k=key, v=var: self._on_bool_setting_changed(k, v),
                )
                # Place checkboxes horizontally with consistent gap, wrapping to next row when needed
                widget.pack(side=tk.LEFT, padx=(0, 18))
                self.entries[key] = widget

                checkbox_col += 1
                if checkbox_col >= max_checkbox_cols:
                    checkbox_col = 0
                    row += 1
            else:
                # For non-checkbox items, start on a new row if we're mid-checkbox-row
                if checkbox_col > 0:
                    checkbox_col = 0
                    row += 1

                if config["type"] in ["int", "float"]:
                    var = tk.StringVar(value=str(value) if value is not None else "")
                else:
                    var = tk.StringVar(value=value if value is not None else "")
                ttk.Label(settings_frame, text=config["label"]).grid(row=row, column=0, sticky="w", padx=5, pady=2)
                entry = ttk.Entry(settings_frame, textvariable=var, width=config.get("width", 40))
                entry.grid(row=row, column=1, sticky="we", padx=5, pady=2)
                entry.bind("<FocusIn>", lambda e: e.widget.selection_clear())
                self.entries[key] = entry
                row += 1
            self.vars[key] = var

        settings_frame.columnconfigure(1, weight=1)

        # Buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        self.save_button = ttk.Button(
            button_frame, text="Save Settings", command=self.save_settings_button, style="Action.TButton"
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.reset_button = ttk.Button(
            button_frame, text="Reset to Defaults", command=self.reset_settings_button, style="Action.TButton"
        )
        self.reset_button.pack(side=tk.LEFT, padx=5)

    def _on_bool_setting_changed(self, key, var):
        """Apply boolean settings immediately to runtime logic."""
        try:
            self.settings[key] = bool(var.get())
            if hasattr(self.logic, "set_runtime_settings"):
                self.logic.set_runtime_settings(self.settings)
        except Exception as e:
            self.log_message(f"Failed to apply setting '{key}': {e}", is_error=True)

    def save_settings_button(self):
        old_nas_dir = self.settings.get("nas_dir")
        old_logging_dir = self.settings.get("logging_dir")

        new_settings = {}
        for config in self.settings_config:
            key = config["key"]
            var = self.vars[key]
            if config["type"] == "bool":
                new_settings[key] = var.get()
            elif config["type"] == "int":
                try:
                    new_settings[key] = int(var.get())
                except ValueError:
                    # Use default value if invalid integer
                    new_settings[key] = 50 if key == "max_foxglove_files" else 0
                    self.log_message(f"Invalid integer for {config['label']}, using default.", is_error=True)
            elif config["type"] == "float":
                try:
                    new_settings[key] = float(var.get())
                except ValueError:
                    # Use default value if invalid float
                    new_settings[key] = 1.0 if key == "bazel_bag_gui_rate" else 0.0
                    self.log_message(f"Invalid number for {config['label']}, using default.", is_error=True)
            else:
                new_settings[key] = var.get()

        # Save the new settings
        self.save_settings(new_settings)

        # Now that self.settings is updated, get the new values
        new_nas_dir = self.settings.get("nas_dir")
        new_logging_dir = self.settings.get("logging_dir")

        # Check if the nas_dir has changed and trigger the callback
        if self.on_nas_dir_changed and new_nas_dir != old_nas_dir:
            if isinstance(new_nas_dir, str) and new_nas_dir:
                self.on_nas_dir_changed(new_nas_dir)

        # Check if the logging_dir has changed and trigger the callback
        if self.on_logging_dir_changed and new_logging_dir != old_logging_dir:
            if isinstance(new_logging_dir, str) and new_logging_dir:
                self.on_logging_dir_changed(new_logging_dir)

        self.log_message("Settings saved successfully.")

    def reset_settings_button(self):
        self.reset_settings()
        for config in self.settings_config:
            key = config["key"]
            value = self.get_setting(key)
            if config["type"] == "bool":
                self.vars[key].set(value if value is not None else True)
            else:
                self.vars[key].set(value)
        self.log_message("Settings reset to defaults.")

    def get_entry_widgets(self):
        # Return only entry widgets (not checkbuttons)
        return tuple(self.entries[config["key"]] for config in self.settings_config if config["widget"] == "entry")
