"""
Settings Manager for the Triage GUI application.

Provides a centralised class for loading, saving, validating, and resetting
application settings with type-safe access and atomic disc writes.

Usage::

    from src.utils.settings_manager import SettingsManager

    manager = SettingsManager()

    # Read a value
    nas_dir = manager.get("nas_dir")

    # Update in-memory (no I/O)
    manager.update({"nas_dir": "/new/path"})

    # Atomically persist to disc
    success, error = manager.save()

    # Reset everything to factory defaults
    manager.reset()
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from .constants import DEFAULT_SETTINGS, SETTINGS_FILE_PATH
from .logger import get_logger

logger = get_logger(__name__)

#: Validation schema for each known settings key.
#: Keys: ``type`` (Python type), ``required`` (bool), ``min_val``/``max_val``
#: (numeric bounds), ``is_path`` (bool — path should ideally be a directory).
_SETTINGS_SCHEMA: Dict[str, Any] = {
    "bazel_tools_viz_cmd": {"type": str, "required": True},
    "bazel_bag_gui_cmd": {"type": str, "required": True},
    "bazel_working_dir": {"type": str, "required": False},
    "nas_dir": {"type": str, "required": False, "is_path": True},
    "backup_nas_dir": {"type": str, "required": False, "is_path": True},
    "logging_dir": {"type": str, "required": False, "is_path": True},
    "max_foxglove_files": {"type": int, "required": False, "min_val": 1, "max_val": 1000},
    "bazel_bag_gui_rate": {"type": float, "required": False, "min_val": 0.01},
    "open_foxglove_in_browser": {"type": bool, "required": False},
    "single_instance_video": {"type": bool, "required": False},
    "single_instance_rosbag": {"type": bool, "required": False},
    "auto_open_event_log_for_tg": {"type": bool, "required": False},
    "event_log_viewer_as_tab": {"type": bool, "required": False},
}


def validate_settings(settings: dict) -> List[Tuple[str, str]]:
    """Validate *settings* against :data:`_SETTINGS_SCHEMA`.

    Checks:
    - Required fields are present and non-empty.
    - Values have the expected Python type.
    - Numeric values are within their declared :data:`min_val`/:data:`max_val` bounds.
    - (Informational) Path strings exist on the filesystem when ``is_path`` is
      set; violations are still returned as errors so callers can warn the user,
      but the absence of a NAS mount is not considered fatal.

    Args:
        settings: The settings dict to validate (usually ``SettingsManager.settings``).

    Returns:
        A list of ``(field_name, human_readable_message)`` tuples, one per
        issue found.  An empty list means the settings are fully valid.
    """
    errors: List[Tuple[str, str]] = []

    for field, rules in _SETTINGS_SCHEMA.items():
        value = settings.get(field)

        # Required fields must be present and non-empty
        if rules.get("required"):
            if value is None or value == "":
                errors.append((field, f"Required setting '{field}' is missing or empty"))
                continue

        # Skip absent optional fields
        if value is None:
            continue

        # Type check
        expected_type = rules.get("type")
        if expected_type is not None:
            # Allow plain int where float is expected (Python subtype relationship)
            type_ok = isinstance(value, expected_type)
            if not type_ok and expected_type is float and isinstance(value, int):
                type_ok = True
            if not type_ok:
                errors.append(
                    (
                        field,
                        f"Setting '{field}' should be {expected_type.__name__}, "
                        f"got {type(value).__name__} (value: {value!r})",
                    )
                )
                continue  # Skip further checks on wrong-typed value

        # Numeric range checks
        if "min_val" in rules and isinstance(value, (int, float)):
            if value < rules["min_val"]:
                errors.append(
                    (
                        field,
                        f"Setting '{field}' value {value} is below minimum {rules['min_val']}",
                    )
                )

        if "max_val" in rules and isinstance(value, (int, float)):
            if value > rules["max_val"]:
                errors.append(
                    (
                        field,
                        f"Setting '{field}' value {value} exceeds maximum {rules['max_val']}",
                    )
                )

        # Path existence (informational — mount may be absent)
        if rules.get("is_path") and isinstance(value, str) and value:
            if not os.path.exists(value):
                errors.append(
                    (
                        field,
                        f"Path for '{field}' does not exist: {value}",
                    )
                )
            elif not os.path.isdir(value):
                errors.append(
                    (
                        field,
                        f"Path for '{field}' is not a directory: {value}",
                    )
                )

    return errors


class SettingsManager:
    """Centralised manager for application settings.

    Handles loading from disc, atomic persistence, reset to defaults, and
    individual key access/update.  All default values live in
    ``src/utils/constants.py`` so they only need updating in one place.

    Attributes:
        settings_path: Path to the JSON settings file on disc.
        settings: The currently active settings dictionary (in-memory).
    """

    def __init__(self, settings_path: str = SETTINGS_FILE_PATH) -> None:
        self.settings_path = settings_path
        self.settings: dict = self.load()

    # ------------------------------------------------------------------
    # Core persistence operations
    # ------------------------------------------------------------------

    def load(self) -> dict:
        """Load settings from disc, falling back to defaults if absent or corrupt.

        Returns:
            A settings dictionary that always contains every key from
            ``DEFAULT_SETTINGS`` (user values take precedence where present).
        """
        if not os.path.exists(self.settings_path):
            logger.info("Settings file not found — using defaults (%s)", self.settings_path)
            return DEFAULT_SETTINGS.copy()

        try:
            with open(self.settings_path, "r", encoding="utf-8") as fh:
                user_settings = json.load(fh)

            if not isinstance(user_settings, dict):
                logger.error("Settings file is not a JSON object — using defaults")
                return DEFAULT_SETTINGS.copy()

            # Merge: user values take precedence; missing keys fall back to defaults
            merged = DEFAULT_SETTINGS.copy()
            merged.update(user_settings)
            logger.debug("Settings loaded from %s", self.settings_path)

            # Validate and log any issues (non-fatal — app continues with loaded values)
            issues = validate_settings(merged)
            for field, msg in issues:
                # Path-missing warnings are expected when NAS/LOGGING is unmounted
                level = "debug" if "does not exist" in msg or "not a directory" in msg else "warning"
                getattr(logger, level)("Settings validation: %s", msg)

            return merged

        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("Settings file parse error (%s) — using defaults", exc)
            return DEFAULT_SETTINGS.copy()
        except (IOError, OSError) as exc:
            logger.error("Settings file read error (%s) — using defaults", exc)
            return DEFAULT_SETTINGS.copy()

    def save(self, updates: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
        """Atomically persist current settings (optionally merging *updates* first).

        The write is done to a ``.tmp`` sibling file and then atomically renamed
        to the real path to prevent corruption on crash.

        Args:
            updates: Optional dict of key/value pairs to merge before saving.

        Returns:
            ``(True, None)`` on success or ``(False, error_message)`` on failure.
        """
        if updates:
            self.settings.update(updates)

        temp_path = self.settings_path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as fh:
                json.dump(self.settings, fh, indent=4, ensure_ascii=False)
            os.replace(temp_path, self.settings_path)
            logger.debug("Settings saved to %s", self.settings_path)
            return True, None

        except (IOError, OSError) as exc:
            return False, f"File error: {exc}"
        except (TypeError, ValueError) as exc:
            return False, f"Data error: {exc}"
        except Exception as exc:  # noqa: BLE001
            return False, f"Unexpected error: {exc}"
        finally:
            # Remove temp file if os.replace failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def reset(self) -> None:
        """Reset all settings to application defaults and persist immediately."""
        self.settings = DEFAULT_SETTINGS.copy()
        self.save()
        logger.debug("Settings reset to defaults")

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if the key is absent."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a single *key* in-memory without persisting to disc.

        Call :meth:`save` afterwards to persist the change.
        """
        self.settings[key] = value

    def update(self, updates: dict) -> None:
        """Merge *updates* into the current in-memory settings without persisting."""
        self.settings.update(updates)

    def as_dict(self) -> dict:
        """Return a shallow copy of all current settings."""
        return self.settings.copy()

    def validate_path(self, key: str) -> Tuple[bool, str]:
        """Check that the directory path stored under *key* exists and is readable.

        Returns:
            ``(True, "")`` if the path is valid, or ``(False, message)`` if not.
        """
        path = self.get(key)
        if not path:
            return False, f"Setting '{key}' is not configured"
        if not os.path.exists(path):
            return False, f"Path does not exist: {path}"
        if not os.path.isdir(path):
            return False, f"Path is not a directory: {path}"
        if not os.access(path, os.R_OK):
            return False, f"Permission denied: {path}"
        return True, ""

    def validate(self) -> List[Tuple[str, str]]:
        """Validate the current in-memory settings and return all issues found.

        Delegates to the module-level :func:`validate_settings` function.

        Returns:
            A list of ``(field_name, message)`` tuples; empty on success.
        """
        return validate_settings(self.settings)
