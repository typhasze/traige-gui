```mermaid
graph TD
    %% Layer 1: Presentation Layer (UI)
    subgraph UI_Layer [Presentation Layer]
        Main[main.py: Entry Point]
        GM[gui_manager.py: GUI Manager]
        FET[file_explorer_tab.py]
        ST[settings_tab.py]
    end

    %% Layer 2: Orchestration Layer (Core)
    subgraph Core_Layer [Coordination Layer]
        CL[core_logic.py: Core Logic Engine]
        PHM[ProcessHealthMonitor: Background Thread]
    end

    %% Layer 3: Logic & Utility Layer (Back-end)
    subgraph Logic_Layer [Logic & Utility Layer]
        FEL[file_explorer_logic.py]
        SPL[symlink_playback_logic.py]
        UTL[utils.py]
    end

    %% Layer 4: External Systems
    subgraph External_Systems [External Systems & Data]
        NAS[(NAS Storage / rosbags)]
        Tools[Analysis Tools: Foxglove, mpv, Bazel]
        Config[JSON Settings File]
    end

    %% Relationships and Data Flow
    Main -->|Initializes| GM
    GM -->|Coordinates| FET
    GM -->|Coordinates| ST
    GM <-->|Actions & States| CL

    CL <-->|Retrieves/Saves| Config
    CL -->|Delegates| FEL
    CL -->|Delegates| SPL
    CL -->|Monitors PIDs| PHM

    FEL <-->|Directory Scans| NAS
    SPL -->|Creates Symlinks| NAS
    CL -->|Launches| Tools
    PHM -.->|Kills Dead Procs| Tools
```
