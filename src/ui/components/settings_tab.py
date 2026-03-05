import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ...utils.constants import DEFAULT_SETTINGS, SETTINGS_FILE_PATH
from ...utils.logger import get_logger
from ...utils.settings_manager import SettingsManager

logger = get_logger(__name__)


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

        # Delegate all persistence to SettingsManager
        self._manager = SettingsManager(SETTINGS_FILE_PATH)
        self.settings = self._manager.settings  # convenient alias (same dict object)

        if hasattr(self.logic, "set_runtime_settings"):
            self.logic.set_runtime_settings(self.settings)
        self.on_nas_dir_changed: Optional[Callable[[str], None]] = None
        self.on_logging_dir_changed: Optional[Callable[[str], None]] = None
        self.create_widgets()
        # Initialize logic with settings after loading them
        self.logic.update_search_paths(self.settings.get("nas_dir"), self.settings.get("backup_nas_dir"))

    def load_settings(self) -> dict:
        """Reload settings from disc and refresh the in-memory alias."""
        self._manager.settings = self._manager.load()
        self.settings = self._manager.settings
        logger.debug("Settings reloaded via SettingsManager")
        return self.settings

    def save_settings(self, settings_dict=None) -> tuple:
        """Save current settings to disc, optionally merging *settings_dict* first.

        Returns ``(True, None)`` on success or ``(False, error_message)`` on failure.
        After saving, the logic layer is updated with the new values and the
        search paths are refreshed.
        """
        success, error = self._manager.save(settings_dict)
        if success:
            # Keep the alias pointing at the same dict after any mutations
            self.settings = self._manager.settings
            self.logic.update_search_paths(self.settings.get("nas_dir"), self.settings.get("backup_nas_dir"))
            logger.debug("Settings persisted successfully")
        else:
            logger.error("Failed to save settings: %s", error)
        return success, error

    def reset_settings(self) -> None:
        """Reset all settings to application defaults and persist immediately."""
        self._manager.reset()
        self.settings = self._manager.settings

    def get_setting(self, key: str):
        """Return the value for *key* from the current settings."""
        return self._manager.get(key)

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
        """Apply boolean settings immediately to runtime logic and save to disk."""
        try:
            new_value = bool(var.get())
            self.settings[key] = new_value
            logger.debug("Bool setting changed: %s = %s", key, new_value)

            # Save to disk immediately
            self.save_settings(self.settings)

            # Update runtime settings in logic
            if hasattr(self.logic, "set_runtime_settings"):
                self.logic.set_runtime_settings(self.settings)
        except Exception as e:
            self.log_message(f"Failed to apply setting '{key}': {e}", is_error=True)
            logger.exception("Failed to apply setting '%s'", key)

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
                    new_settings[key] = DEFAULT_SETTINGS.get(key, 0)
                    self.log_message(f"Invalid integer for {config['label']}, using default.", is_error=True)
            elif config["type"] == "float":
                try:
                    new_settings[key] = float(var.get())
                except ValueError:
                    new_settings[key] = DEFAULT_SETTINGS.get(key, 0.0)
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
        # Temporarily block the bool-change callback (vars.set triggers it)
        # by patching save_settings to a no-op during the UI refresh loop.
        _real_save = self.save_settings
        self.save_settings = lambda *a, **kw: (True, None)  # type: ignore[assignment]
        try:
            for config in self.settings_config:
                key = config["key"]
                value = self.get_setting(key)
                if config["type"] == "bool":
                    self.vars[key].set(value if value is not None else True)
                else:
                    self.vars[key].set(value)
        finally:
            self.save_settings = _real_save
        self.log_message("Settings reset to defaults.")

    def get_entry_widgets(self):
        # Return only entry widgets (not checkbuttons)
        return tuple(self.entries[config["key"]] for config in self.settings_config if config["widget"] == "entry")
