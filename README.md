# Triage GUI

A comprehensive Python GUI application for managing, viewing, and analyzing autonomous vehicle rosbag data, event logs, and video recordings. This tool streamlines the workflow for accessing MCAP files, playing back data with Foxglove Studio or Bazel Bag GUI, and correlating events with video footage.

## Features

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
- **Foxglove Studio**: Launch with single or multiple MCAP files
  - Desktop or browser mode support
  - Optimized batch file loading
  - Command-line length protection
- **Bazel Bag GUI**: Play rosbags with configurable playback rate
  - Single file or symlink-based multi-file playback
  - Timestamp-aware launching from event logs
- **Video playback**: Launch mpv player at specific timestamps
- **Process management**: Track and terminate running playback processes

### 🎛️ Settings Tab
- **Bazel configuration**: Configure Bazel commands and working directory
- **Playback rate**: Adjust Bazel bag GUI playback speed
- **Directory paths**: Set data, backup, and LOGGING directory locations
- **Foxglove options**: Choose between desktop or browser mode
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

## Project Structure

```
traige-gui/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Application entry point
│   ├── gui_manager.py             # Main GUI coordinator
│   ├── core_logic.py              # Core application logic
│   ├── logic/
│   │   ├── file_explorer_logic.py # File operations logic
│   │   └── symlink_playback_logic.py # Symlink management
│   ├── ui/
│   │   └── components/
│   │       ├── file_explorer_tab.py  # File browser UI
│   │       ├── foxglove_tab.py       # Foxglove MCAP UI
│   │       └── settings_tab.py       # Settings UI
│   └── utils/
│       └── utils.py               # Utility functions
├── requirements.txt
└── README.md
```

## Installation

### Prerequisites
- Python 3.7+
- Foxglove Studio (optional, for MCAP playback)
- Bazel (optional, for bazel bag gui)
- mpv (optional, for video playback)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd traige-gui
```

2. Install required Python dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Install external tools:
```bash
# Foxglove Studio - https://foxglove.dev/download
# Bazel - https://bazel.build/install
# mpv - https://mpv.io/installation/
```

## Running the Application

Launch the application with:

```bash
python src/main.py
```

## Usage Guide

### Opening MCAP Files

**Method 1: File Explorer**
1. Navigate to your data directory using the File Explorer tab
2. Select one or more MCAP files
3. Click "Open with Foxglove" or "Open with Bazel"

**Method 2: Link Analysis**
1. Copy a Foxglove link or file URL
2. Paste into the "Analyze Link" field
3. Click "Analyze" to navigate to the file
4. File will be automatically highlighted

### Viewing Event Logs

1. Navigate to an `event_log_*.txt` file in File Explorer
2. Double-click to open the Event Log Viewer
3. Select an event row to see details
4. Use action buttons:
   - **Play Video at Selected Time**: Launch video at event timestamp
   - **Play Bazel at Selected Time**: Launch rosbag playback at closest timestamp
   - **Show MCAP in Explorer**: Navigate to corresponding MCAP file

### Managing Processes

- Click "Show Process Status" to view running Foxglove/Bazel instances
- Each process shows PID and runtime
- Close the application to automatically terminate all spawned processes

### Configuring Settings

1. Open the Settings tab
2. Configure:
   - Bazel commands and working directory
   - Data directory paths
   - LOGGING directory (external drive path, default: `/media/{username}/LOGGING`)
   - Foxglove browser/desktop preference
   - Playback rates and file limits
3. Click "Save Settings" to persist changes

## Keyboard Shortcuts

### General
- **Escape**: Clear text selections
- **Ctrl+Q**: Quit application
- **F1**: Show keyboard shortcuts help
- **F5**: Refresh current tab
- **Ctrl+P**: Show process status

### File Operations
- **Ctrl+O**: Open selected file
- **Ctrl+F**: Open with Foxglove
- **Ctrl+B**: Open with Bazel
- **Ctrl+C**: Copy file path
- **Ctrl+M**: Open in file manager
- **Ctrl+A**: Select all text in entry fields

### Navigation
- **Ctrl+L**: Navigate to LOGGING directory
- **Enter**: Navigate into selected folder / Open file
- **Double-Click**: Open file or navigate into folder
- **Backspace**: Navigate to parent directory (File Explorer)
- **Arrow Keys**: Navigate file lists with keyboard

### Event Log Viewer
- **V**: Play video at selected time
- **B**: Play Bazel at selected time
- **S**: Show MCAP in Explorer
- **Ctrl+F** or **/**: Focus search field
- **Ctrl+A**: Select all text in search/filter fields
- **Escape**: Clear search filter

## Performance Optimizations

- **Batch file validation**: Efficient validation of multiple MCAP files
- **Command-line length protection**: Prevents "Argument list too long" errors
- **Process health monitoring**: Automatic cleanup of terminated processes
- **Lazy loading**: Directories loaded on-demand for better performance
- **Cached operations**: File metadata cached to reduce disk I/O
- **Non-blocking operations**: Background threading for builds and long-running tasks
- **Real-time feedback**: Animated status indicators for loading and building operations

## Configuration

Settings are stored in `~/.foxglove_gui_settings.json` and include:
- Bazel tool commands and working directory
- Data and backup directory paths
- LOGGING directory path (for external drive access)
- Foxglove browser/desktop preference
- Playback rate and file limits

## Troubleshooting

**MCAP files not found:**
- Check that files exist in `~/data` or configured data directory
- Verify paths in Settings tab

**Foxglove/Bazel won't launch:**
- Ensure tools are installed and in PATH
- Check Bazel working directory in Settings
- View process status for error messages

**Event log timestamp issues:**
- Application supports multiple timestamp formats
- Check that MCAP filenames follow format: `VEHICLE_YYYY-MM-DD-HH-MM-SS_N.mcap`

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for:
- Bug reports
- Feature requests
- Performance improvements
- Documentation updates

## License

This project is licensed under the MIT License - see the LICENSE file for details.
