<div align="center">

1. Copy folder to home
2. run terminal ./traige-gui/src/main.py

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

A comprehensive Python GUI application for managing, viewing, and analyzing autonomous vehicle rosbag data, event logs, and video recordings. Built with tkinter for maximum compatibility and minimal dependencies.

## ✨ Features

### 📁 File Explorer Tab
- **Navigate directories**: Browse through data folders with intuitive file explorer
- **Quick access shortcuts**:
  - Home button: Navigate to configured NAS data directory
  - LOGGING button: Navigate to external LOGGING drive (Ctrl+L)
  - Back button: Return to previous directory
- **Visual file icons**: File type indicators (🎥 MCAP, 📁 folders, 📄 text, 🖼️ images, etc.)
- **MCAP file management**: Select single or multiple MCAP files for playback
- **Link analysis**: Paste Foxglove, mpv, or Bazel command links to automatically navigate to files
  - Supports Foxglove URLs with `ds.url` parameters
  - Supports direct file paths (~/data/... or /home/.../data/...)
  - Supports mpv commands with timestamps
  - Supports Bazel commands with file paths
- **File highlighting**: Visual highlighting of analyzed files in the explorer
- **Quick access**: Double-click files to open or navigate folders
- **History navigation**: Back button to navigate through browsing history
- **Search/filter**: Filter files in current directory by name
  - Type any key in file list to start filtering
- **NAS connection monitoring**: Automatic detection and warnings for unmounted/inaccessible NAS drives

### 📊 Event Log Viewer
- **Structured view**: View event logs in a sortable, searchable table
- **Column display**: Shows timestamp, event description, criticality level, and UI mode
- **Video playback**: Play video at selected event timestamp (via mpv) - press 'V'
- **Bazel playback options**:
  - Launch at event timestamp with `--start-offset` - press 'B'
  - Play from beginning of bag - press 'C'
- **File navigation**: Automatically navigate to and highlight corresponding MCAP file - press 'L'
- **Event selection**: Click events to see details and access playback options
- **Timestamp parsing**: Intelligent parsing of various timestamp formats
- **Search functionality**: Quick search with Ctrl+F or '/' (Vim-style)
- **Event count display**: Shows total number of events in the log

### 🎥 Playback Integration
- **Bazel Bag GUI**: Play rosbags with configurable playback rate
  - Single file or symlink-based multi-file playback
  - Timestamp-aware launching from event logs with `--start-offset`
  - Accurate event timestamp playback (respects 300-second bag duration)
  - Real-time loading status with animated progress indicators
  - Command-line length protection to prevent "Argument list too long" errors
- **Video playback**: Launch mpv player at specific timestamps
  - Synchronized with event log timestamps
  - Automatic video file selection based on timestamp
- **Single instance mode**: Optional single instance for video and rosbag players
  - Prevents multiple simultaneous playback sessions
  - Configurable per player type in Settings
- **Process management**: Track and terminate running playback processes
  - View PID and runtime for all processes with status indicators (🟢/🔴)
  - Automatic process health monitoring (background thread)
  - Automatic cleanup on application exit
  - Detection of long-running processes (>2 hours)

### 🎛️ Settings Tab
- **Bazel configuration**:
  - Bazel working directory (default: ~/av-system/catkin_ws/src)
  - Bazel Tools Viz command
  - Bazel Bag GUI command
- **Playback rate**: Adjust Bazel bag GUI playback speed (default: 1.0)
- **Directory paths**:
  - NAS Directory (primary data location)
  - Backup NAS Directory
  - LOGGING Directory (external drive, default: /media/{username}/LOGGING)
- **File limits**: Configure maximum MCAP files for Foxglove (default: 50)
- **Single instance mode**: Toggle single instance behavior for video and rosbag players
- **Persistent settings**: Settings saved as JSON configuration (~/.foxglove_gui_settings.json)
- **Reset to defaults**: One-click restoration of default settings
- **Dynamic callbacks**: Automatic updates to file explorer when directories change

### 🔧 Advanced Features
- **Multi-file selection**: Select and open multiple MCAP files simultaneously
- **Symlink management**: Automatic symlink creation for multi-bag playback
  - Temporary directory: /tmp/selected_bags_symlinks
  - Automatic cleanup on exit
- **Build integration**: Build Bazel workspace with `bazel build //...` command
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
- **Error handling**: Comprehensive error reporting and validation
  - NAS connection detection and warnings
  - Permission error handling
  - Timeout protection for file operations
- **Clipboard integration**: Copy file paths to clipboard
- **System integration**: Open directories in native file manager
  - Cross-platform support (Linux/macOS/Windows)

## 📂 Project Structure

<details>
<summary>Click to expand project structure</summary>

```
traige-gui/
├── src/
│   ├── __init__.py
│   ├── main.py                         # 🚀 Application entry point
│   ├── gui_manager.py                  # 🎨 Main GUI coordinator
│   ├── logic/
│   │   ├── __init__.py
│   │   ├── core.py                     # ⚙️  Core application logic
│   │   ├── file_explorer_logic.py      # 📂 File operations & caching
│   │   └── symlink_playback_logic.py   # 🔗 Symlink management
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── gui_manager.py              # 🎨 GUI orchestration
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── file_explorer_tab.py    # 🗂️  File browser & event viewer
│   │       └── settings_tab.py         # ⚙️  Settings interface
│   └── utils/
│       ├── __init__.py
│       ├── constants.py                # 🔧 Centralized constants & defaults
│       ├── file_operations.py          # 📁 Cross-platform file utilities
│       ├── utils.py                    # 🛠️  Utility functions
│       └── __pycache__/
├── requirements.txt                     # 📦 Dependencies (none needed!)
├── pyproject.toml                      # 🔧 Tool configurations
├── README.md                           # 📖 This file
├── architecture_v2.md                  # 📐 System architecture
└── REFACTORING_SUMMARY.md             # ✅ Code improvement documentation
```

| Component      | Required   | Purpose                            |
| -------------- | ---------- | ---------------------------------- |
| Python 3.7+    | ✅ Yes      | Runtime environment (with tkinter) |
| Bazel          | ✅ Yes      | Rosbag GUI and build commands      |
| mpv            | 🔷 Optional | Video playback from event logs     |
| NAS Connection | ✅ Yes      | Access to rosbag data              |

## 🔧 Recent Code Improvements

### Centralized Constants Module
A new `src/utils/constants.py` module consolidates all configuration values, default settings, and constants. This provides:
- **Single source of truth** for all configuration values
- **Default settings dictionary** (paths, file limits, process parameters)
- **File icon mappings** for consistent UI display
- **Performance parameters** (cache sizes, timeouts, monitoring intervals)
- **Cross-platform compatibility** handling

### Extracted Common File Operations
New `src/utils/file_operations.py` module provides reusable utilities:
- `open_file_with_default_app()` - Open files with system default application
- `open_directory_in_file_manager()` - Open directories in file explorer
- `open_url_in_browser()` - Open URLs in default browser
- `safe_file_read()` - Safe file reading with error handling
- `safe_file_write()` - Atomic file writing operations

Benefits include eliminated code duplication, consistent error handling, and improved cross-platform support.

### Improved Settings Management
Settings loading and defaults are now centralized, making configuration updates simpler and more maintainable:
- Centralized defaults in `constants.py`
- Standardized settings file path constant
- Simplified loading and reset logic
- All updates in one location

> **📚 Setup Guides:**
> - [NAS Setup Guide](https://ventitechnologies.atlassian.net/wiki/spaces/ACH/pages/763953520/Laptop+Set+Up+Guide+for+TE#NAS-SETUP)
> - [AV-System Clone Guide](https://ventitechnologies.atlassian.net/wiki/spaces/ACH/pages/763953520/Laptop+Set+Up+Guide+for+TE) - Clone `av-system` repo to root directory

### 🔧*Python 3.7+** (with tkinter support)
- **Bazel** (required, for bazel bag gui and build commands)
- **mpv** (optional, for video playback from event logs)

- **NAS SETUP** https://ventitechnologies.atlassian.net/wiki/spaces/ACH/pages/763953520/Laptop+Set+Up+Guide+for+TE#NAS-SETUP

**Step 1:** Clone the repository
```bash
git clone <repository-url>
cd traige-gui
```

**Step 2:** Install tkinter (if not available)
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# macOS - included with Python from python.org
```

**Step 3:** No pip packages required! 🎉
> The application uses only Python standard library

**Step 4 (Optional):** Install mpv for video playback
```bash
# Ubuntu/Debian
sudo apt-get install mpv

# macOS
brew install mpv
```

**Step 5:** Add convenience function to `~/.bashrc`
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
4. Click "Rosbag Playback" or press Ctrl+B

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
2. Double-click to open the Event Log Viewer window
3. Browse events in the sortable table (shows timestamp, description, criticality, UI mode)
4. Select an event row to enable action buttons
5. Use action buttons or keyboard shortcuts:
   - **Video Timestamp (V)**: Launch video at exact event timestamp with mpv
   - **Rosbag Timestamp (B)**: Launch rosbag playback at exact event timestamp with `--start-offset`
   - **Current Rosbag (C)**: Play the current MCAP file from the beginning
   - **Rosbag Location (L)**: Navigate to and highlight the corresponding MCAP file
6. Use search filter (Ctrl+F or /) to find specific events

### 🔨 Building Bazel Workspace

1. Click the "Build..." button in the main window
2. Real-time build output will stream to the console log
3. Animated status indicator shows build progress ("Building...", "Building....", etc.)
4. Build command: `bazel build //...`
5. Status bar updates on completion or failure

### 🔄 Managing Processes

- Click "Running Processes" (or press Ctrl+P) to view running Foxglove/Bazel/mpv instances
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
   - **Playback rates and file limits**
     - Bazel Bag GUI Rate: Default 1.0
     - Max Foxglove Files: Default 50
3. Click "Save Settings" to persist changes
4. Click "Reset to Defaults" to restore default settings
5. Settings are stored in: ~/.foxglove_gui_settings.json

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
- **Ctrl+O**: Open selected file
- **Ctrl+B**: Open with Bazel Bag GUI
- **Ctrl+C**: Copy file path
- **Ctrl+M**: Open in file manager
- **Ctrl+F**: Open with Foxglove
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

</td><td>

### 📊 Event Log Viewer
- **V**: Video Timestamp
- **B**: Rosbag Timestamp
- **S**: Same as B (alternative)
- **C**: Current Rosbag (from start)
- **L**: Navigate to Rosbag Location
- **Ctrl+F** or **/**: Focus search field
- **Escape**: Clear search filter

</td></tr>
</table>

---

## 📘 Usage Guide

### 📂 Opening MCAP Files

#### Method 1: File Explorer
1. Navigate to your data directory using the File Explorer tab
2. Files are displayed with icons: 🎥 (MCAP), 📁 (folders), 📄 (text files)
3. Select one or more MCAP files (Ctrl+Click for multiple)
4. Click "Rosbag Playback" or press Ctrl+B

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
2. Double-click to open the Event Log Viewer window
3. Browse events in the sortable table (shows timestamp, description, criticality, UI mode)
4. Select an event row to enable action buttons
5. Use action buttons or keyboard shortcuts:
   - **Video Timestamp (V)**: Launch video at exact event timestamp with mpv
   - **Rosbag Timestamp (B)**: Launch rosbag playback at exact event timestamp with `--start-offset`
   - **Current Rosbag (C)**: Play the current MCAP file from the beginning
   - **Rosbag Location (L)**: Navigate to and highlight the corresponding MCAP file
6. Use search filter (Ctrl+F or /) to find specific events

### 🔨 Building Bazel Workspace

1. Click the "Build..." button in the main window
2. Real-time build output will stream to the console log
3. Animated status indicator shows build progress ("Building...", "Building....", etc.)
4. Build command: `bazel build //...`
5. Status bar updates on completion or failure

### 🔄 Managing Processes

- Click "Running Processes" (or press Ctrl+P) to view running Foxglove/Bazel/mpv instances
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
   - **Playback rates and file limits**
     - Bazel Bag GUI Rate: Default 1.0
     - Max Foxglove Files: Default 50
3. Click "Save Settings" to persist changes
4. Click "Reset to Defaults" to restore default settings
5. Settings are stored in: ~/.foxglove_gui_settings.json

---

## �️ Development & Architecture

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
- `utils.py` - Miscellaneous helper functions

### Code Organization
Recently completed refactorings have improved code maintainability:
- **Constants consolidation**: All configuration in `src/utils/constants.py`
- **Shared utilities**: Common file operations extracted to prevent duplication
- **Settings management**: Centralized defaults and loading logic
- **Type hints**: Improved IDE support and code clarity

### Future Improvements
See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) for detailed roadmap including:
- ✅ [Complete] Centralize constants module
- ✅ [Complete] Extract file operations utilities
- ✅ [Complete] Improve settings management
- 📋 [Planned] Create Settings Manager class
- 📋 [Planned] Add comprehensive unit tests
- 📋 [Planned] Extract event log viewer to separate component
- 📋 [Planned] Implement structured logging

---

## �🔧 Troubleshooting

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
- Check "Running Processes" (Ctrl+P) for error messages
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
- Check "Running Processes" to see if mpv launched successfully
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

**File Management:**
- Symlink directory: `/tmp/selected_bags_symlinks` (for multi-file playback)
- File info cache: 1000 entry limit
- Process health monitoring: Every 10 seconds
- Long-running process threshold: 2 hours

---

## 🔍 Features Summary

**Performance Optimizations:**
- Efficient validation of multiple MCAP files
- Command-line length protection: Prevents "Argument list too long" errors
- Process health monitoring: Automatic cleanup of terminated processes
- File metadata cached to reduce disk I/O
- Non-blocking operations: Background threading for builds and long-running tasks
- Batch directory operations for faster navigation

**User Experience:**
- Visual file type indicators with emojis
- Real-time process status with animated indicators
- Comprehensive keyboard shortcuts for all operations
- Intelligent link parsing (Foxglove, mpv, Bazel, direct paths)
- NAS connection detection and helpful error messages
- Cross-platform file manager integration

**Reliability:**
- Background process health monitoring
- Automatic zombie process cleanup
- Timeout protection for file operations
- Permission error detection
- Empty directory detection (unmounted NAS)
- Settings validation and defaults
---

## 📚 Documentation & Resources

- [**Refactoring Summary**](REFACTORING_SUMMARY.md) - Comprehensive guide to recent code improvements, architecture decisions, and future roadmap
- [**Architecture v2**](architecture_v2.md) - System architecture diagram and component interactions
- [**README**](README.md) - This file; complete user guide and feature documentation
