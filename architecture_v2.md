```mermaid
graph TB
    %% Entry Point
    Main[main.py<br/>Entry Point]

    %% Presentation Layer
    subgraph UI [" Presentation Layer "]
        GM[GUI Manager<br/>Orchestrator]
        FET[File Explorer<br/>Browse & Navigate]
        EventViewer[Event Log Viewer<br/>Timeline Analysis]
        ST[Settings<br/>Configuration]
    end

    %% Core Business Logic
    subgraph Core [" Core Logic Layer "]
        CL[Core Logic<br/>Process Management]
        PHM[Health Monitor<br/>Background Thread]
    end

    %% Support Modules
    subgraph Logic [" Logic & Utilities "]
        FEL[File Explorer Logic<br/>Caching & Scanning]
        SPL[Symlink Manager<br/>Multi-file Playback]
        UTL[Utilities<br/>Icons & Formatting]
    end

    %% External Systems
    subgraph External [" External Systems "]
        Storage[(Storage<br/>NAS & LOGGING)]
        Tools[Analysis Tools<br/>Foxglove, mpv, Bazel]
        Config[(Settings File<br/>JSON Config)]
    end

    %% Main Flow
    Main --> GM

    %% UI Layer Connections
    GM --> FET
    GM --> ST
    GM --> EventViewer
    GM <--> CL

    %% Core Layer Connections
    CL --> PHM
    CL --> FEL
    CL --> SPL
    CL --> UTL

    %% UI to Logic
    FET --> FEL
    EventViewer --> CL
    ST <--> Config

    %% Core to External
    CL <--> Config
    CL --> Tools
    FEL <--> Storage
    SPL --> Storage
    PHM -.-> Tools
    Tools -.-> Storage

    %% Styling
    classDef entryStyle fill:#e1f5ff,stroke:#01579b,stroke-width:4px,color:#000
    classDef uiStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:3px,color:#000
    classDef coreStyle fill:#fff3e0,stroke:#e65100,stroke-width:3px,color:#000
    classDef logicStyle fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px,color:#000
    classDef externalStyle fill:#fce4ec,stroke:#880e4f,stroke-width:2px,color:#000

    class Main entryStyle
    class GM,FET,EventViewer,ST uiStyle
    class CL,PHM coreStyle
    class FEL,SPL,UTL logicStyle
    class Storage,Tools,Config externalStyle
```

## 📋 Architecture Summary

### **4-Layer Architecture**

**1. Presentation Layer**
- GUI Manager orchestrates all UI components
- File Explorer for browsing and navigation
- Event Log Viewer for timeline analysis
- Settings for configuration management

**2. Core Logic Layer**
- Process lifecycle management
- External tool launching (Foxglove, mpv, Bazel)
- Background health monitoring thread

**3. Logic & Utilities**
- File operations with caching (1000 entries)
- Multi-file symlink management
- Icon mapping and formatting utilities

**4. External Systems**
- Storage: NAS and LOGGING drives
- Analysis Tools: Foxglove, mpv, Bazel
- Settings: JSON configuration file

---

## 🔄 Key Workflows

| Workflow | Flow |
|----------|------|
| **File Playback** | User selects files → File Explorer → Core Logic → Launch Tools |
| **Event Analysis** | Open event log → Select timestamp → Launch video/rosbag at exact time |
| **Configuration** | Edit settings → Save to JSON → Callbacks update UI |
| **Process Management** | Health monitor checks every 10s → Clean up dead processes |

---

## 🚀 Key Features

- **Smart Caching**: 1000-entry file cache for fast navigation
- **Health Monitoring**: Automatic process cleanup every 10 seconds
- **Multi-file Support**: Symlink-based batch rosbag playback
- **Link Parsing**: Supports Foxglove, mpv, and Bazel command formats
- **NAS Detection**: Automatic connection monitoring and warnings
