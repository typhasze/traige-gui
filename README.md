<div align="center">

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
  - Home button: Navigate to configured data directory
  - LOGGING button: Navigate to external LOGGING drive
  - Back button: Return to previous directory
- **MCAP file management**: Select single or multiple MCAP files for playback
- **Link analysis**: Paste Foxglove or file links to automatically navigate to files
- **File highlighting**: Visual highlighting of analyzed files in the explorer
- **Quick access**: Double-click files to open or navigate folders
- **History navigation**: Back button to navigate through browsing history
- **Search/filter**: Filter files in current directory by name

### 📊 Event Log Viewer
- **Structured view**: View event logs in a sortable, searchable table
- **Column display**: Shows timestamp, event description, criticality level, and UI mode
- **Video playback**: Play video at selected event timestamp (via mpv)
- **Bazel playback**: Launch Bazel Bag GUI with MCAP file closest to event timestamp
- **File navigation**: Automatically navigate to and highlight corresponding MCAP file
- **Event selection**: Click events to see details and access playback options
- **Timestamp parsing**: Intelligent parsing of various timestamp formats

### 🎥 Playback Integration
- **Bazel Bag GUI**: Play rosbags with configurable playback rate
  - Single file or symlink-based multi-file playback
  - Timestamp-aware launching from event logs with `--start-offset`
  - Accurate event timestamp playback (respects 300-second bag duration)
  - Real-time loading status with animated progress indicators
- **Video playback**: Launch mpv player at specific timestamps
  - Synchronized with event log timestamps
  - Automatic video file selection based on timestamp
- **Process management**: Track and terminate running playback processes
  - View PID and runtime for all processes
  - Automatic cleanup on application exit

### 🎛️ Settings Tab
- **Bazel configuration**: Configure Bazel commands and working directory
- **Playback rate**: Adjust Bazel bag GUI playback speed
- **Directory paths**: Set data, backup, and LOGGING directory locations
- **File limits**: Configure maximum files for batch operations
- **Persistent settings**: Settings saved as JSON configuration

### 🔧 Advanced Features
- **Multi-file selection**: Select and open multiple MCAP files simultaneously
- **Symlink management**: Automatic symlink creation for multi-bag playback
- **Build integration**: Build Bazel workspace with `bazel build //...` command
  - Real-time build output streaming
  - Animated build status indicator
- **Process monitoring**: View running processes with PID and runtime
- **Background process cleanup**: Automatic zombie process prevention
- **Error handling**: Comprehensive error reporting and validation
- **Clipboard integration**: Copy file paths to clipboard
- **System integration**: Open directories in native file manager

## 📂 Project Structure

<details>
<summary>Click to expand project structure</summary>

```
traige-gui/
├── src/
│   ├── __init__.py
│   ├── main.py                         # 🚀 Application entry point
│   ├── gui_manager.py                  # 🎨 Main GUI coordinator
│   ├── core_logic.py                   # ⚙️  Core application logic
│   ├── logic/
│   │   ├── file_explorer_logic.py      # 📂 File operations
│   │   └── symlink_playback_logic.py   # 🔗 Symlink management
│   ├── ui/
│   │   └── components/
│   │       ├── file_explorer_tab.py    # 🗂️  File browser & event viewer
│   │       └── settings_tab.py         # ⚙️  Settings interface
│   └── utils/
│       └── utils.py                    # 🛠️  Utility functions
├── requirements.txt                     # 📦 Dependencies (none needed!)
├── .pre-commit-config.yaml             # ✅ Code quality hooks
├── pyproject.toml                      # 🔧 Tool configurations
└── README.md                           # 📖 This file
```

| Component | Required | Purpose |
|-----------|----------|---------|
| Python 3.7+ | ✅ Yes | Runtime environment (with tkinter) |
| Bazel | ✅ Yes | Rosbag GUI and build commands |
| mpv | 🔷 Optional | Video playback from event logs |
| NAS Connection | ✅ Yes | Access to rosbag data |

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

# Option 1: Direct execution
./src/main.py

# Option 2: Python command
python3 src/main.py

# Option 3: Convenience function (after adding to .bashrc)
triage_gui
```

---

## 📘thon3 src/main.py
# or📂 Opening MCAP Files

#### Method 1: File Explorer

## Usage Guide

### Opening MCAP Files

#### Method 2: Link Analysis
1. Navigate to your data directory using the File Explorer tab
2. Select one or more MCAP files
3. Click "Rosbag Playback" (Bazel Bag GUI)

**Method 2: Link Analysis**
1. Copy a file link or URL containing MCAP path information
2. Paste into the "Analyze Link" field in File Explorer
3. Click "Analyze" to navigate to the file location
4. File will be automatically highlighted in yellow

### 📊 Viewing Event Logs

1. Navigate to an `event_log_*.txt` file in File Explorer
2. Double-click to open the Event Log Viewer window
3. Select an event row to see details
4. Use action buttons:
   - **Play Video at Selected Time**: Launch video at exact event timestamp with mpv
   - **Play Bazel at Selected Time**: Launch rosbag playback at exact event timestamp with `--start-offset`
   - **Show MCAP in Explorer**: Navigate to and highlight the corresponding MCAP file

### 🔨 Building Bazel Workspace

1. Click the "Build" button in the main window
2. Real-time build output will stream to the console
3. Animated status indicator shows build progress
4. Build command: `bazel build //...`

### 🔄 Managing Processes

- Click "Show Process Status" to view running Foxglove/Bazel instances
- Each process shows PID and runtime
- Close the application to automatically terminate all spawned processes

### ⚙️ Configuring Settings

1. Open the Settings tab
2. Configure:
   - Bazel commands and working directory
   - Data directory paths
   - LOGGING directory (external drive path, default: `/media/{username}/LOGGING`)
   - Foxglove browser/desktop preference
   - Playback rates and file limits
3. Click "Save Settings" to persist changes

---

## ⌨️ Keyboard Shortcuts

<table>
<tr><td>

### 🔧 General
- **Escape**: Clear text selections
</td><td>

### 📁*Ctrl+Q**: Quit application
- **F1**: Show keyboard shortcuts help
- **F5**: Refresh current tab
- **Ctrl+P**: Show process status

</td></tr>
<tr><td>

### 🧭 File Operations
- **Ctrl+O**: Open selected file
- **Ctrl+B**: Open with Bazel Bag GUI
- **Ctrl+C**: Copy file path
</td><td>

### 📊*Ctrl+M**: Open in file manager
- **Ctrl+A**: Select all text in entry fields

### Navigation
- **Ctrl+L**: Navigate to LOGGING directory
- **Enter**: Navigate into selected folder / Open file
</td></tr>
</table>

---

## ⚡**Double-Click**: Open file or navigate into folder
- **Backspace**: Navigate to parent directory (File Explorer)
- **Arrow Keys**: Navigate file lists with keyboard

### Event Log Viewer
---

## ⚙️**V**: Play video at selected time
- **B**: Play Bazel at selected time
- **S**: Show MCAP in Explorer
- **Ctrl+F** or **/**: Focus search field
- **Ctrl+A**: Select all text in search/filter fields
- **Escape**: Clear search filter

---

## 🔧 Troubleshooting

<details>
<summary><b>MCAP files not found</b></summary>

**Solutionion**: Efficient validation of multiple MCAP files
- **Command-line length protection**: Prevents "Argument list too long" errors
- **Process health monitoring**: Automatic cleanup of terminated processes
- Ensure NAS is connected

</details>

<details>
<summary><b>Bazel won't launch</b></summary>

**Solutions**: File metadata cached to reduce disk I/O
- **Non-blocking operations**: Background threading for builds and long-running tasks
</details>

<details>
<summary><b>Event log timestamp issues</b></summary>

</details>

<details>
<summary><b>Video playback not working</b></summary>

**Solutioncators for loading and building operations

</details>

<details>
<parameter name="summary"><b>Link analysis segmentation fault</b></summary>

**Solution

Settings are stored in `~/.foxglove_gui_settings.json` and include:
- Bazel tool commands and working directory (e.g., `bazel run //tools/bag:gui`)
- Data and backup directory paths
- LOGGING directory path (for external drive access)
- Playback rate (default: 1.0)
- File operation limits

## Troubleshooting

**MCAP files not found:**
- Check that files exist in `~/data` or configured data directory
- Verify paths in Settings tab

**Bazel won't launch:**
- Ensure Bazel is installed and in PATH
- Check Bazel working directory in Settings tab
- Verify Bazel command is correct: `bazel run //tools/bag:gui`
- View process status for error messages

**Event log timestamp issues:**
- Application supports multiple timestamp formats
- Check that MCAP filenames follow format: `VEHICLE_YYYY-MM-DD-HH-MM-SS_N.mcap`
- Each rosbag should be 300 seconds duration for accurate offset calculation

**Video playback not working:**
- Install mpv: `sudo apt-get install mpv`
- Check that video files exist in the `video/` directory parallel to event logs

**Link analysis segmentation fault:**
- This has been fixed with safety checks and delayed highlighting
- If it persists, ensure you're using the latest version
