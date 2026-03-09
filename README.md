<div align="center">

Quick start: clone this repo and run `./src/main.py`.

# 🚗 Triage GUI

### A powerful Python GUI for autonomous vehicle data analysis

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Bazel](https://img.shields.io/badge/bazel-required-green.svg)](https://bazel.build/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*Streamline your workflow for analyzing MCAP rosbag data, event logs, and video recordings*

[Features](#features) • [Installation](#installation) • [Usage](#usage-guide) • [Shortcuts](#keyboard-shortcuts)

</div>

---

## 📖 Overview

Python GUI for managing and analyzing autonomous vehicle rosbag data, event logs, and video recordings. Built with tkinter for compatibility and minimal dependencies.

## ✨ Features

### 📁 File Explorer Tab
- **Navigate directories**: Browse data folders in an intuitive file explorer
- **Quick access shortcuts**:
  - Home button: Navigate to configured NAS data directory
  - LOGGING button: Navigate to external LOGGING drive (Ctrl+L)
  - Back button: Return to previous directory
- **Compact action toolbar**: Fast access to `Open`, `Copy`, `Manager`, `Foxglove`, `Rosbag`, `Viz`, `Topic`, `Plot`, `Build`, and `Procs`
- **Visual file icons**: File type indicators (🎥 MCAP, 📁 folders, 📄 text, 🖼️ images, etc.)
- **MCAP file management**: Select single or multiple MCAP files for playback
- **Link analysis**: Paste Foxglove, mpv, or Bazel links to jump to files
  - Supports Foxglove URLs with `ds.url` parameters
  - Supports direct file paths (~/data/... or /home/.../data/...)
  - Supports mpv commands with timestamps
  - Supports Bazel commands with file paths
- **File highlighting**: Visual highlighting of analyzed files in the explorer
  - Event log files are highlighted in green for quick identification
- **Quick access**: Double-click files to open, or folders to navigate
- **History navigation**: Back button to navigate through browsing history
- **Search/filter**: Filter files in the current directory by name
  - Type any key in file list to start filtering
  - Press `Ctrl+E` to focus the search filter explicitly
- **NAS connection monitoring**: Automatic detection and warnings for unmounted/inaccessible NAS drives
- **Clipboard integration**: Copy one or multiple selected file paths to the clipboard

### 📊 Event Log Viewer
- **Flexible viewing modes**: Open event logs as windows or notebook tabs
  - Tab mode: Embedded tabs in main notebook window (default)
  - Window mode: Independent floating windows
  - Configurable via Settings: "Open event log viewer as tab"
- **Auto-open for TG folders**: Automatically open event logs when navigating to TG-XXXX folders
  - Configurable via Settings: "Auto-open event log for TG folders"
  - Enabled by default
  - Auto-open triggers when a TG folder contains exactly one vehicle folder
  - Also triggers when navigating directly into a vehicle folder that is inside a TG folder
- **Structured view**: Searchable event table
- **Column display**: Timestamp, event description, criticality, and UI mode
- **Video playback**: Play video at selected event timestamp (via mpv) - press 'V'
  - Double-click an event row to play video immediately
- **Bazel playback options**:
  - Launch at event timestamp with `--start-offset` - press 'B'
  - Play from beginning of bag - press 'C'
- **File navigation**: Jump to and highlight the corresponding MCAP file - press 'L'
- **Event selection**: Select events to view details and playback actions
- **Timestamp parsing**: Intelligent parsing of various timestamp formats
- **Search functionality**: Quick search with Ctrl+F or '/' (Vim-style)
  - Shows live filter feedback ("No matches found" / "Showing X of Y")
- **Event count display**: Shows total events in the log
- **Tab management**: Double-click event log tabs to close them
- **Large file handling**: Warns for large event logs and loads rows asynchronously with a loading indicator

### 🎥 Playback Integration
- **Bazel Bag GUI**: Play rosbags with configurable rate
  - Single file or symlink-based multi-file playback
  - Timestamp-aware launching from event logs with `--start-offset` (includes 30-second pre-buffer)
  - When the 30-second buffer crosses the boundary into the preceding bag, both MCAPs are automatically loaded via symlinks
  - Accurate event timestamp playback (respects 300-second bag duration)
  - Real-time loading status with animated progress indicators
  - Command-line length protection to prevent "Argument list too long" errors
- **Foxglove launch behavior**:
  - Multiple selected MCAP files automatically use desktop mode (browser mode supports single file only)
  - Enforces max file count and command-length safety limits for multi-file launches
- **Video playback**: Launch mpv player at specific timestamps
  - Synchronized with event log timestamps
  - Automatic video file selection based on timestamp
- **Single instance mode**: Optional single-instance behavior for video and rosbag players
  - Prevents multiple simultaneous playback sessions
  - Configurable per player type in Settings
- **Process management**: Track and terminate playback processes
  - View PID and runtime for all processes with status indicators (🟢/🔴)
  - Automatic process health monitoring (background thread)
  - Automatic cleanup on application exit
  - Detection of long-running processes (>2 hours)

### 🎛️ Settings Tab
- **Bazel configuration**:
  - Bazel working directory (default: ~/av-system/catkin_ws/src)
- **Playback rate**: Set Bazel bag GUI playback speed (default: 1.0)
- **Directory paths**:
  - NAS Directory (primary data location)
  - Backup NAS Directory
  - LOGGING Directory (external drive, default: /media/{username}/LOGGING)
- **File limits**: Configure maximum MCAP files for Foxglove (default: 50)
- **Single instance mode**: Toggle single instance behavior for video and rosbag players
- **Event log preferences**:
  - Auto-open event logs when entering TG-XXXX folders
  - Choose between tab or window mode for event log viewers
- **Persistent settings**: Saved to JSON (~/.foxglove_gui_settings.json)
- **Settings validation**: Automatic validation of paths, types, and value ranges
- **Reset to defaults**: One-click restoration of default settings
- **Dynamic callbacks**: Automatic updates to file explorer when directories change

### 🔧 Advanced Features
- **Extra Bazel tools**: Launch additional AV tooling directly from the GUI
  - `Topic` button runs `bazel run //tools/topic:gui`
  - `Plot` button runs `bazel run //tools/plot`
  - Both run from the configured Bazel working directory (`~/av-system/catkin_ws/src` by default)
- **Multi-file selection**: Select and open multiple MCAP files simultaneously
- **Symlink management**: Automatic symlink creation for multi-bag playback
  - Temporary directory: /tmp/selected_bags_symlinks
  - Automatic cleanup on exit
- **Build integration**: Run `bazel build //...` from the app
  - Real-time build output streaming
  - Animated build status indicator with dots
  - Non-blocking background threading
- **Process monitoring**: View running processes with PID and runtime
  - Real-time status indicators (🟢 running / 🔴 stopped)
  - Background health monitoring thread
  - Periodic cleanup every 10 seconds
- **Background process cleanup**: Automatic zombie process prevention
- **Performance optimizations**:
  - File info caching to reduce disk I/O
  - Batch directory operations
  - Efficient directory scanning
  - Pre-allocated list reservations
- **Error handling**: Robust error reporting and validation
  - NAS connection detection and warnings
  - Permission error handling
  - Timeout protection for file operations
- **System integration**: Open directories in native file manager
  - Cross-platform support (Linux/macOS/Windows)

## 📂 Project Structure

```
traige-gui/
├── src/
│   ├── __init__.py
│   ├── main.py                         # 🚀 Application entry point
│   ├── ui/
│   │   ├── gui_manager.py              # 🎨 Main GUI coordinator & Tkinter Log Handler
│   │   ├── __init__.py
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── event_log_viewer.py     # 📊 Event log viewer component (window & tab logic)
│   │       ├── file_explorer_tab.py    # 🗂️ File browser and event-log driven playback/navigation
│   │       └── settings_tab.py         # ⚙️ Settings interface
│   ├── logic/
│   │   ├── __init__.py
│   │   ├── core.py                     # ⚙️ Core application logic & process management
│   │   ├── file_explorer_logic.py      # 📂 File info caching & directory utilities
│   │   └── symlink_playback_logic.py   # 🔗 Multi-bag symlink management
│   └── utils/
│       ├── __init__.py
│       ├── constants.py                # 🔧 Centralized paths, cache limits & default configurations
│       ├── file_operations.py          # 📁 Cross-platform file/directory/URL open utilities
│       ├── logger.py                   # 📝 Structured logging system (File + Tkinter Handler)
│       ├── settings_manager.py         # ⚙️ Type-safe JSON settings persistence
│       └── utils.py                    # 🛠️ Directory scanning & file icon mapping
├── pyproject.toml                      # 🔧 Tool configurations (Black, Isort, Bandit)
└── README.md
```

| Component      | Required   | Purpose                            |
| -------------- | ---------- | ---------------------------------- |
| Python 3.7+    | ✅ Yes      | Runtime environment (with tkinter) |
| Bazel          | ✅ Yes      | Rosbag GUI and build commands      |
| mpv            | 🔷 Optional | Video playback from event logs     |
| NAS Connection | ✅ Yes      | Access to rosbag data              |

## 🛠 Installation

### Prerequisites
- **Python 3.7+** (with tkinter support)
- **Bazel** (required, for bag GUI and build commands)
- **mpv** (optional, for video playback from event logs)
- **NAS setup**: [NAS Setup Guide](https://ventitechnologies.atlassian.net/wiki/spaces/ACH/pages/763953520/Laptop+Set+Up+Guide+for+TE#NAS-SETUP)
- **av-system repo**: Clone to `~/av-system` — [Laptop Set Up Guide](https://ventitechnologies.atlassian.net/wiki/spaces/ACH/pages/763953520/Laptop+Set+Up+Guide+for+TE)

**Step 1:** Clone the repository
```bash
git clone <repository-url>
cd traige-gui
```

**Step 2 :** Install mpv for video playback
```bash
# Ubuntu/Debian
sudo apt-get install mpv
sudo snap install foxglove-studio
```

**Step 3 (Optional):** Add convenience function to `~/.bashrc`
```bash
triage_gui() {
    cd
    nohup ./traige-gui/src/main.py &
}
```

Then reload: `source ~/.bashrc`

---

## 🎮 Running the Application

> ⚠️ **Important:** Ensure NAS is connected before launching!

**Launch options:**

```bash
# Option 1: Direct execution
./src/main.py

# Option 2: Python command
python3 src/main.py

# Option 3: Convenience function (after adding to .bashrc)
triage_gui
```

---

## 📘 Usage Guide

### 📂 Opening MCAP Files

#### Method 1: File Explorer
1. Navigate to your data directory using the File Explorer tab
2. Files are displayed with icons: 🎥 (MCAP), 📁 (folders), 📄 (text files)
3. Select one or more MCAP files (Ctrl+Click for multiple)
4. Click `Rosbag` or press `Ctrl+B`
5. To open selected bags in Foxglove instead, click `Foxglove` or press `Ctrl+F`

#### Method 2: Link Analysis
1. Copy a file link, URL, or command containing MCAP path information:
   - Foxglove URLs (with `ds.url` parameter)
   - Direct file paths (~/data/... or /home/.../data/...)
   - mpv commands (e.g., `mpv --start=3649 https://...`)
   - Bazel commands (e.g., `bazel run //tools/bag:gui ~/data/file.mcap`)
2. Paste into the "Analyze Link" field in File Explorer
3. Click "Analyze" to navigate to the file location
4. File will be automatically highlighted in yellow

### 📊 Viewing Event Logs

1. Navigate to an `event_log_*.txt` file in File Explorer
2. Double-click to open the Event Log Viewer
  - Opens as a notebook tab by default
  - Can be configured to open as a separate window in Settings ("Open event log viewer as tab")
3. **Auto-open feature**: Enabled by default for TG folders and configurable in Settings
  - Triggers when exactly one vehicle folder is found under the TG folder
  - Also triggers when navigating directly into a vehicle folder inside a TG folder
4. Browse events in the sortable table (timestamp, description, criticality, UI mode)
5. Select an event row to enable action buttons
6. Use action buttons or keyboard shortcuts:
   - **Video Timestamp (V)**: Launch video at exact event timestamp with mpv
   - **Rosbag Timestamp (B)**: Launch rosbag playback at exact event timestamp with `--start-offset`
   - **Current Rosbag (C)**: Play the current MCAP file from the beginning
   - **Rosbag Location (L)**: Navigate to and highlight the corresponding MCAP file
7. Use search (Ctrl+F or /) to find events
  - Viewer shows live filter status ("No matches found" / "Showing X of Y")
  - Large files display a warning and load asynchronously
8. **Close tabs**: Double-click on event log tabs to close them (when using tab mode)

### 🔨 Building Bazel Workspace

1. Click the `Build` button in the main window
2. Real-time build output will stream to the console log
3. Animated status indicator shows build progress ("Building...", "Building....", etc.)
4. Build command: `bazel build //...`
5. Status bar updates on completion or failure

### 🔄 Managing Processes

- Click `Procs` (or press `Ctrl+P`) to view running Foxglove/Bazel/mpv instances
- Each process shows:
  - Status indicator: 🟢 (running) or 🔴 (stopped)
  - Process name and PID
  - Runtime duration
- Background health monitor checks processes every 10 seconds
- Long-running processes (>2 hours) are logged for awareness
- Close the application to automatically terminate all spawned processes

### ⚙️ Configuring Settings

1. Open the Settings tab
2. Configure:
   - **Bazel commands and working directory**
     - Default working dir: ~/av-system/catkin_ws/src
   - **Data directory paths**
     - NAS Directory: Primary data location
     - Backup NAS Directory: Secondary data location
   - **LOGGING directory**: External drive path (default: /media/{username}/LOGGING)
   - **Foxglove browser/desktop preference**
   - **Single instance mode**: Prevent multiple simultaneous players
     - Video player (mpv)
     - Rosbag player (Bazel Bag GUI)
   - **Event log viewer preferences**
     - Auto-open event log for TG-XXXX folders: Default true
     - Open event log viewer as tab: Default true
   - **Playback rates and file limits**
     - Bazel Bag GUI Rate: Default 1.0
     - Max Foxglove Files: Default 50
3. Click "Save Settings" to persist changes
4. Click "Reset to Defaults" to restore default settings
5. Settings are stored in: ~/.foxglove_gui_settings.json
6. Settings are automatically validated when saved

---

## ⌨️ Keyboard Shortcuts

<table>
<tr><td>

### 🔧 General
- **Escape**: Clear text selections / Clear search filter
- **Ctrl+Q**: Quit application
- **F1**: Show keyboard shortcuts help
- **F5**: Refresh current tab
- **Ctrl+P**: Show process status

</td><td>

### 🧭 File Operations
- **Ctrl+O**: Open selected item
- **Ctrl+B**: Launch Rosbag playback
- **Ctrl+C**: Copy selected path(s)
- **Ctrl+M**: Open current folder in file manager
- **Ctrl+F**: Launch Foxglove
- **Ctrl+E**: Focus file explorer search filter
- **Ctrl+A**: Select all text in entry fields

</td></tr>
<tr><td>

### 📂 Navigation
- **Ctrl+L**: Navigate to LOGGING directory
- **Enter**: Navigate into selected folder / Open file
- **Backspace**: Navigate to parent directory
- **Arrow Keys**: Navigate file lists
- **Any Key**: Start filtering (in file list)
- **Down/Up**: Navigate from search to list
- **Buttons only**: `Topic` launches `topic-gui`, `Plot` launches `av-plot`

</td><td>

### 📊 Event Log Viewer
- **V**: Play video at selected event timestamp
- **B**: Play Bazel at selected event timestamp
- **C**: Play Bazel from the start of the current bag
- **S** or **L**: Show related MCAP / rosbag location
- **Ctrl+F** or **/**: Focus search field
- **Escape**: Clear search filter and refocus the event list
- **Ctrl+F4**: Close event viewer tab or window
- **Double-click tab**: Close event viewer tab

</td></tr>
</table>

---

## 🏗️ Development & Architecture

### Modular Design
The codebase follows a layered architecture with clear separation of concerns:

**Presentation Layer** (`src/ui/`)
- `gui_manager.py` - Orchestrates all UI components
- `components/file_explorer_tab.py` - File browser and event log viewer
- `components/settings_tab.py` - Configuration interface

**Logic Layer** (`src/logic/`)
- `core.py` - Core business logic and process management
- `file_explorer_logic.py` - File operations, caching, and directory scanning
- `symlink_playback_logic.py` - Multi-file playback support

**Utilities** (`src/utils/`)
- `constants.py` - Centralized configuration and constants
- `file_operations.py` - Cross-platform file utilities and error handling
- `settings_manager.py` - Type-safe settings management with validation
- `logger.py` - Structured logging to file and GUI widget
- `utils.py` - Miscellaneous helper functions

### Code Organization
- **Constants consolidation**: All configuration in `src/utils/constants.py`
- **Shared utilities**: Common file operations extracted to prevent duplication
- **Settings Manager**: Type-safe settings class with validation and atomic persistence
- **Structured logging**: Dual-output logging to file and GUI widget with proper handlers
- **Event log viewer component**: Reusable viewer widget for window or tab embedding
- **Type hints**: Improved IDE support and code clarity throughout

---

## 🔧 Troubleshooting

<details>
<summary><b>MCAP files not found</b></summary>

**Solution**:
- Check that files exist in ~/data or configured NAS directory
- Verify paths in Settings tab
- Ensure NAS is mounted (check for warning messages in log)
- Application will display warnings if:
  - NAS directory doesn't exist
  - NAS directory is empty (not mounted)
  - NAS directory is not accessible (permission denied)

</details>

<details>
<summary><b>Bazel won't launch</b></summary>

**Solutions**:
- Ensure Bazel is installed and in PATH
- Check Bazel working directory in Settings tab (default: ~/av-system/catkin_ws/src)
- Verify Bazel command is correct in Settings:
  - Default: `bazel run //tools/bag:gui`
- Check `Procs` (Ctrl+P) for error messages
- Ensure av-system repository is cloned to the correct location

</details>

<details>
<summary><b>Event log timestamp issues</b></summary>

**Solution**:
- Application supports multiple timestamp formats automatically
- Check that MCAP filenames follow format: `VEHICLE_YYYY-MM-DD-HH-MM-SS_N.mcap`
- Each rosbag should be 300 seconds duration for accurate offset calculation
- Verify that the event log and MCAP files are in the same directory structure

</details>

<details>
<summary><b>Video playback not working</b></summary>

**Solution**:
- Install mpv: `sudo apt-get install mpv` (Ubuntu/Debian) or `brew install mpv` (macOS)
- Check that video files exist in the `video/` directory parallel to event logs
- Verify video file naming matches expected format
- Check `Procs` to see if mpv launched successfully
- Single instance mode: Disable in Settings if you want multiple videos playing

</details>

<details>
<summary><b>Link analysis segmentation fault</b></summary>

**Solution**:
- This has been fixed with safety checks and delayed highlighting
- If it persists, ensure you're using the latest version
- Try restarting the application
- Check log messages for specific error details

</details>

<details>
<summary><b>Performance issues with large directories</b></summary>

**Solution**:
- Application uses optimized batch operations and caching
- File info cache limit: 1000 entries
- Use search/filter to narrow down visible files
- Performance features include:
  - Efficient directory scanning
  - File metadata caching
  - Pre-allocated list operations
  - Background threading for long operations

</details>

---

## 📝 Configuration & Constants

Settings are stored in `~/.foxglove_gui_settings.json` with defaults defined in `src/utils/constants.py`.

### Application Constants
All constants are centralized in `src/utils/constants.py` for easy maintenance:

**Path Constants:**
- `DEFAULT_DATA_PATH` - Primary data directory (~/data)
- `DEFAULT_BACKUP_PATH` - Backup data directory
- `DEFAULT_BAZEL_WORKING_DIR` - Bazel workspace location
- `DEFAULT_LOGGING_DIR` - External LOGGING drive (/media/{username}/LOGGING)
- `SYMLINK_DIR` - Temporary symlink location for multi-file playback (/tmp/selected_bags_symlinks)
- `SETTINGS_FILE_PATH` - Settings file location (~/.foxglove_gui_settings.json)

**Performance Parameters:**
- `PROCESS_MONITOR_INTERVAL` - Health check frequency (10 seconds)
- `LONG_RUNNING_PROCESS_THRESHOLD` - Alert threshold (2 hours)
- `PROCESS_SHUTDOWN_TIMEOUT` - Termination timeout (2 seconds)
- `FILE_INFO_CACHE_SIZE_LIMIT` - Maximum cached file entries (1000)

**Logging:**
- Log directory: `~/.traige_gui/logs`
- Log file: `~/.traige_gui/logs/traige_gui.log`
- Rotating logs: 5 MB per file, keeps 3 backups

### Persistent Settings
Settings are stored in `~/.foxglove_gui_settings.json` with the following structure:

**Bazel Configuration:**
- `bazel_tools_viz_cmd`: Default "bazel run //tools/viz"
- `bazel_bag_gui_cmd`: Default "bazel run //tools/bag:gui"
- `bazel_working_dir`: Default "~/av-system/catkin_ws/src"
- `bazel_bag_gui_rate`: Default 1.0 (playback speed)

**Directory Paths:**
- `nas_dir`: Primary data directory (default: ~/data)
- `backup_nas_dir`: Secondary data directory (default: ~/data/psa_logs_backup_nas3)
- `logging_dir`: External LOGGING drive (default: /media/{username}/LOGGING)

**Player Configuration:**
- `open_foxglove_in_browser`: Default true
- `single_instance_video`: Default true (prevents multiple mpv instances)
- `single_instance_rosbag`: Default true (prevents multiple Bazel Bag GUI instances)
- `max_foxglove_files`: Default 50 (maximum files for Foxglove)

**Event Log Preferences:**
- `auto_open_event_log_for_tg`: Default true (automatically open event logs in TG-XXXX folders)
- `event_log_viewer_as_tab`: Default true (open event logs as tabs instead of windows)

**File Management:**
- Symlink directory: `/tmp/selected_bags_symlinks` (for multi-file playback)
- File info cache: 1000 entry limit
- Process health monitoring: Every 10 seconds
- Long-running process threshold: 2 hours

**Event Log Management:**
- Auto-open event logs when entering TG-XXXX folders (configurable)
- Auto-open only triggers when a TG folder has exactly one vehicle subfolder
- Tab or window mode for event log viewers (configurable)
- Double-click tabs to close event log viewers
- Multi-line event description support with proper parsing

---
