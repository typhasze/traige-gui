import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ...utils.constants import DEFAULT_SETTINGS, SETTINGS_FILE_PATH
from ...utils.logger import get_logger
from ...utils.settings_manager import SettingsManager
from .tooltip import attach_tooltip

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

        self._manager = SettingsManager(SETTINGS_FILE_PATH)
        self.settings = self._manager.settings
        self._setting_tooltips = {
            "bazel_working_dir": "Directory where Bazel commands run.",
            "nas_dir": "Primary NAS data root used by File Explorer.",
            "backup_nas_dir": "Fallback data root when primary NAS path is unavailable.",
            "logging_dir": "Path to LOGGING drive used by quick navigation.",
            "max_foxglove_files": "Maximum number of MCAP files to open in Foxglove at once.",
            "bazel_bag_gui_rate": "Playback rate for Bazel rosbag GUI.",
            "open_foxglove_in_browser": "Open single MCAP in browser Foxglove instead of desktop app.",
            "single_instance_video": "Keep only one MPV video process at a time.",
            "single_instance_rosbag": "Keep only one Bazel rosbag process at a time.",
            "auto_open_event_log_for_tg": "Auto-open event logs when entering TG folders.",
            "event_log_viewer_as_tab": "Open event viewer inside main notebook tab.",
        }

        self.logic.set_runtime_settings(self.settings)
        self.on_nas_dir_changed: Optional[Callable[[str], None]] = None
        self.on_logging_dir_changed: Optional[Callable[[str], None]] = None
        self.on_branch_changed: Optional[Callable[[], None]] = None
        self.create_widgets()
        self.logic.update_search_paths(self.settings.get("nas_dir"), self.settings.get("backup_nas_dir"))

    def load_settings(self) -> dict:
        """Reload settings from disc and refresh the in-memory alias."""
        self._manager.settings = self._manager.load()
        self.settings = self._manager.settings
        self.logic.set_runtime_settings(self.settings)
        logger.debug("Settings reloaded via SettingsManager")
        return self.settings

    def save_settings(self, settings_dict=None) -> tuple:
        """Save current settings to disc, merging *settings_dict* first if given.

        Returns ``(True, None)`` on success or ``(False, error_message)`` on failure.
        """
        success, error = self._manager.save(settings_dict)
        if success:
            self.settings = self._manager.settings
            self.logic.set_runtime_settings(self.settings)
            self.logic.update_search_paths(self.settings.get("nas_dir"), self.settings.get("backup_nas_dir"))
            logger.debug("Settings persisted successfully")
        else:
            logger.error("Failed to save settings: %s", error)
        return success, error

    def reset_settings(self) -> None:
        """Reset all settings to application defaults and persist immediately."""
        self._manager.reset()
        self.settings = self._manager.settings
        self.logic.set_runtime_settings(self.settings)

    def get_setting(self, key: str):
        """Return the value for *key* from the current settings."""
        return self._manager.get(key)

    def create_widgets(self):
        settings_frame = ttk.LabelFrame(self.frame, text="Configuration")
        settings_frame.pack(fill="x", padx=10, pady=10)

        row = 0
        checkbox_col = 0
        max_checkbox_cols = 3
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
                widget.pack(side=tk.LEFT, padx=(0, 18))
                attach_tooltip(widget, self._setting_tooltips.get(key, config["label"]))
                self.entries[key] = widget

                checkbox_col += 1
                if checkbox_col >= max_checkbox_cols:
                    checkbox_col = 0
                    row += 1
            else:
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

        # --- Git Branch row (below Bazel Working Directory) ---
        if checkbox_col > 0:
            row += 1
        git_label = ttk.Label(settings_frame, text="Bazel Git Branch:")
        git_label.grid(row=row, column=0, sticky="w", padx=5, pady=2)

        git_row_frame = ttk.Frame(settings_frame)
        git_row_frame.grid(row=row, column=1, sticky="we", padx=5, pady=2)

        self._git_branch_var = tk.StringVar(value="—")
        self._git_branch_combo = ttk.Combobox(
            git_row_frame, textvariable=self._git_branch_var, width=40, state="readonly"
        )
        self._git_branch_combo.pack(side=tk.LEFT, fill="x", expand=True)
        attach_tooltip(self._git_branch_combo, "Current git branch of the Bazel working directory.")

        refresh_btn = ttk.Button(git_row_frame, text="↻", width=3, command=self._refresh_git_branch)
        refresh_btn.pack(side=tk.LEFT, padx=(4, 0))
        attach_tooltip(refresh_btn, "Refresh branch list from Bazel working directory.")

        checkout_btn = ttk.Button(git_row_frame, text="Checkout", command=self._git_checkout_selected)
        checkout_btn.pack(side=tk.LEFT, padx=(4, 0))
        attach_tooltip(checkout_btn, "Switch to the selected git branch.")

        row += 1
        self.frame.after(200, self._refresh_git_branch)

        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        self.save_button = ttk.Button(
            button_frame, text="Save Settings", command=self.save_settings_button, style="Action.TButton"
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
        attach_tooltip(self.save_button, "Save current settings to ~/.foxglove_gui_settings.json.")
        self.reset_button = ttk.Button(
            button_frame, text="Reset to Defaults", command=self.reset_settings_button, style="Action.TButton"
        )
        self.reset_button.pack(side=tk.LEFT, padx=5)
        attach_tooltip(self.reset_button, "Restore all settings to built-in defaults.")

    def _on_bool_setting_changed(self, key, var):
        """Apply boolean settings immediately to runtime logic and save to disk."""
        try:
            new_value = bool(var.get())
            self.settings[key] = new_value
            logger.debug("Bool setting changed: %s = %s", key, new_value)
            self.save_settings(self.settings)
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

        self.save_settings(new_settings)

        new_nas_dir = self.settings.get("nas_dir")
        new_logging_dir = self.settings.get("logging_dir")

        if self.on_nas_dir_changed and new_nas_dir != old_nas_dir:
            if isinstance(new_nas_dir, str) and new_nas_dir:
                self.on_nas_dir_changed(new_nas_dir)

        if self.on_logging_dir_changed and new_logging_dir != old_logging_dir:
            if isinstance(new_logging_dir, str) and new_logging_dir:
                self.on_logging_dir_changed(new_logging_dir)

        self.log_message("Settings saved successfully.")

    def reset_settings_button(self):
        self.reset_settings()
        # Avoid triggering per-toggle saves while we repopulate all Tk variables.
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

    def _refresh_git_branch(self):
        """Load git branches from the Bazel working directory in a background thread."""
        working_dir = self.get_setting("bazel_working_dir") or ""
        if not working_dir:
            self._git_branch_var.set("(no dir set)")
            return

        def _fetch():
            current, err = self.logic.get_git_branch(working_dir)
            branches, _ = self.logic.get_git_branches(working_dir)
            self.frame.after(0, lambda: self._apply_git_branch_data(current, branches, err))

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_git_branch_data(self, current, branches, error):
        if error:
            self._git_branch_var.set(f"Error: {error}")
            self._git_branch_combo.config(values=[])
            return
        self._git_branch_combo.config(values=branches)
        if current and current in branches:
            self._git_branch_var.set(current)
        elif current:
            self._git_branch_var.set(current)

    def _git_checkout_selected(self):
        branch = self._git_branch_var.get()
        working_dir = self.get_setting("bazel_working_dir") or ""
        if not branch or branch.startswith("Error") or branch == "—":
            self.log_message("No valid branch selected.", is_error=True)
            return
        if not working_dir:
            self.log_message("Bazel working directory is not set.", is_error=True)
            return

        self.log_message(f"Checking out branch '{branch}'...")

        def _do_checkout():
            success, msg = self.logic.git_checkout(working_dir, branch)
            self.frame.after(0, lambda: self._on_checkout_done(success, msg))

        threading.Thread(target=_do_checkout, daemon=True).start()

    def _on_checkout_done(self, success, message):
        if success:
            self.log_message(f"git checkout: {message}")
        else:
            self.log_message(f"git checkout failed: {message}", is_error=True)
        self._refresh_git_branch()
        if self.on_branch_changed:
            self.on_branch_changed()

    def get_entry_widgets(self):
        return tuple(self.entries[config["key"]] for config in self.settings_config if config["widget"] == "entry")
