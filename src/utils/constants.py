"""
Centralized constants for the Triage GUI application.

This module contains all constants used throughout the application,
including default paths, settings, process names, and file type mappings.
"""

import getpass
import os

# ============================================================================
# PATH CONSTANTS
# ============================================================================
DEFAULT_DATA_PATH = os.path.expanduser("~/data")
DEFAULT_BACKUP_PATH = os.path.expanduser("~/data/psa_logs_backup_nas3")
DEFAULT_BAZEL_WORKING_DIR = os.path.expanduser("~/av-system/catkin_ws/src")
DEFAULT_LOGGING_DIR = f"/media/{getpass.getuser()}/LOGGING"
SYMLINK_DIR = "/tmp/selected_bags_symlinks"
SETTINGS_FILE_PATH = os.path.expanduser("~/.foxglove_gui_settings.json")

# ============================================================================
# DEFAULT SETTINGS
# ============================================================================
DEFAULT_SETTINGS = {
    "bazel_tools_viz_cmd": "bazel run //tools/viz",
    "bazel_bag_gui_cmd": "bazel run //tools/bag:gui",
    "bazel_working_dir": DEFAULT_BAZEL_WORKING_DIR,
    "nas_dir": DEFAULT_DATA_PATH,
    "backup_nas_dir": DEFAULT_BACKUP_PATH,
    "logging_dir": DEFAULT_LOGGING_DIR,
    "max_foxglove_files": 50,
    "bazel_bag_gui_rate": 1.0,
    "open_foxglove_in_browser": True,
    "single_instance_video": True,
    "single_instance_rosbag": True,
    "auto_open_event_log_for_tg": True,
    "event_log_viewer_as_tab": True,
    "auto_git_branch_switch": True,
    "git_fetch_on_startup": True,
    "git_default_branch": "develop",
}

# ============================================================================
# PROCESS NAMES
# ============================================================================
PROCESS_NAMES = {
    "FOXGLOVE_STUDIO": "Foxglove Studio",
    "FOXGLOVE_BROWSER": "Foxglove Studio (Browser)",
    "BAZEL_TOOLS_VIZ": "Bazel Tools Viz",
    "BAZEL_BAG_GUI": "Bazel Bag GUI",
    "MPV_VIDEO": "MPV Video",
}

# ============================================================================
# FILE ICONS
# ============================================================================
FILE_ICON_MAP = {
    ".mcap": "🎥",
    ".txt": "📄",
    ".log": "📄",
    ".md": "📄",
    ".py": "📜",
    ".js": "📜",
    ".cpp": "📜",
    ".h": "📜",
    ".c": "📜",
    ".java": "📜",
    ".jpg": "🖼️",
    ".png": "🖼️",
    ".gif": "🖼️",
    ".bmp": "🖼️",
    ".jpeg": "🖼️",
    ".zip": "📦",
    ".tar": "📦",
    ".gz": "📦",
    ".rar": "📦",
    ".pdf": "📕",
    ".json": "⚙️",
    ".xml": "⚙️",
    ".yaml": "⚙️",
    ".yml": "⚙️",
}

DEFAULT_FILE_ICON = "📄"

# ============================================================================
# PERFORMANCE LIMITS
# ============================================================================
FILE_INFO_CACHE_SIZE_LIMIT = 1000
PROCESS_MONITOR_INTERVAL = 10  # seconds
LONG_RUNNING_PROCESS_THRESHOLD = 7200  # 2 hours in seconds
PROCESS_SHUTDOWN_TIMEOUT = 2  # seconds

# ============================================================================
# FOXGLOVE CONSTANTS
# ============================================================================
FOXGLOVE_REMOTE_BASE_URL = "https://foxglove.data.ventitechnologies.net/"
FOXGLOVE_DS_URL = "https://rosbag.data.ventitechnologies.net/"

# ============================================================================
# FILE PATTERNS
# ============================================================================
MCAP_FILE_EXTENSION = ".mcap"
EVENT_LOG_PREFIX = "event_log_"
EVENT_LOG_EXTENSION = ".txt"
TG_FOLDER_PATTERN = r"^TG(-\d+)?$"  # Matches TG or TG-XXXX
VEHICLE_FOLDER_PATTERN = r"^PSA\d+$"  # Matches PSAXXXX
