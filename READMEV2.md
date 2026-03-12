# Triage GUI — Readme V2

## Short Feature Summary

Triage GUI is a Tkinter desktop tool for navigating autonomous-vehicle data folders and launching playback workflows.

- File explorer with history, search filter, quick navigation (`Home`, `LOGGING`, `Back`), and multi-select MCAP support
- Link analysis for Foxglove/MPV/Bazel/path inputs to jump to local data folders and highlight target files
- Event log viewer (tab or window mode) with search, event table, and actions for:
  - video playback via `mpv`
  - rosbag playback via Bazel
  - navigation to related MCAP files
- Playback integrations:
  - Foxglove desktop/browser launch (with safeguards for multi-file and command length)
  - Bazel bag GUI launch (single file or symlink-based multi-file)
  - optional single-instance mode for video and rosbag players
- Process tracking and cleanup (status view, runtime info, health monitor, graceful shutdown cleanup)
- Settings persistence in JSON (`~/.foxglove_gui_settings.json`) with validation and reset-to-default

## Project Structure

```text
traige-gui/
├── pyproject.toml
├── README.md
└── src/
    ├── main.py
    ├── logic/
    │   ├── core.py
    │   ├── file_explorer_logic.py
    │   └── symlink_playback_logic.py
    ├── ui/
    │   ├── gui_manager.py
    │   └── components/
    │       ├── event_log_viewer.py
    │       ├── file_explorer_tab.py
    │       └── settings_tab.py
    └── utils/
        ├── constants.py
        ├── file_operations.py
        ├── logger.py
        ├── settings_manager.py
        └── utils.py
```

## Setup + Installation

### Prerequisites

- Python `3.7+`
- Tkinter runtime (`python3-tk` on many Linux distros)
- Bazel (required for bag GUI / build actions)
- Optional:
  - `mpv` (video-at-timestamp playback)
  - `foxglove-studio` desktop app (desktop launch mode)

### Install

```bash
git clone <your-repo-url>
cd traige-gui
```

Install Tkinter if needed (Linux):

```bash
sudo apt-get update
sudo apt-get install -y python3-tk
```

Optional tools:

```bash
sudo apt-get install -y mpv
sudo snap install foxglove-studio
# Install Bazel and foxglove-studio using your system’s preferred method
```

### Run

```bash
python3 src/main.py
```

## Short Usage Guide

1. Open **Settings** tab first and confirm:
   - `nas_dir`, `backup_nas_dir`, `logging_dir`
   - `bazel_working_dir`
2. Go to **File Explorer** tab and browse your data folder.
3. Select one or more `.mcap` files and use:
   - **Foxglove** to launch Foxglove playback
  - **Rosbag** to launch Bazel bag GUI
4. Open an `event_log_*.txt` file (double-click) to use event actions:
   - play matching video at timestamp
   - launch bag playback at timestamp / from start
   - jump to matching MCAP file
5. Use **Procs** to inspect active processes and statuses.

### Useful Shortcuts

- `F1` open shortcut help
- `F5` refresh current tab
- `Ctrl+Tab` move to next tab (wraps and focuses selected tab)
- `Ctrl+Q` quit app
- `Ctrl+P` show process status

File Explorer (when File Explorer tab is active):

- `Ctrl+F` launch Foxglove
- `Ctrl+B` launch Rosbag playback
- `Ctrl+C` copy selected path(s)
- `Ctrl+M` open current folder in file manager
- `Ctrl+E` focus search filter
- `Ctrl+H` navigate to Home/NAS directory
- `Ctrl+L` navigate to LOGGING directory
- `Backspace` go to parent directory

Event Log Viewer (when Event Log Viewer is active):

- `Ctrl+E` or `/` focus search field
- `Ctrl+V` play video at selected event timestamp
- `Ctrl+B` play Bazel at selected event timestamp
- `Ctrl+C` play Bazel from start of current bag
- `Ctrl+L` locate related MCAP/rosbag
- `Up/Down` move event-row selection
- `Escape` clear search and refocus event list
- `Ctrl+F4` close event viewer tab/window
