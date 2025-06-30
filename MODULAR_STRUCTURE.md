# Modular Codebase Structure

## Overview
The codebase has been refactored to follow a more modular and maintainable architecture with clear separation of concerns.

## New Directory Structure

```
src/
├── core_logic.py                    # Core business logic (unchanged)
├── main.py                          # Original main entry point
├── main_refactored.py              # New main entry point
├── gui_manager.py                   # Original GUI manager (keep for reference)
├── gui_manager_refactored.py       # New modular GUI manager
├── logic/                           # Business Logic Layer
│   ├── __init__.py
│   ├── file_explorer_logic.py      # File system operations
│   ├── foxglove_logic.py           # Foxglove-specific operations
│   ├── mcap_logic.py               # MCAP file operations
│   └── navigation_logic.py         # Navigation and history management
├── gui/                             # GUI Components Layer
│   ├── __init__.py
│   ├── logging_component.py        # Reusable logging widget
│   ├── file_list_component.py      # Reusable file list widget
│   └── button_group.py             # Reusable button group widget
└── utils/                           # Utility Functions
    ├── __init__.py
    ├── utils.py                     # File utilities (existing)
    └── path_utils.py               # Path manipulation utilities
```

## Key Improvements

### 1. Separation of Concerns
- **Business Logic**: Moved to `logic/` modules
- **GUI Components**: Moved to `gui/` modules  
- **Utilities**: Organized in `utils/` modules
- **Main GUI**: Simplified to orchestrate components

### 2. Reusable Components

#### GUI Components (`gui/`)
- **LoggingComponent**: Handles all logging/status display
- **FileListComponent**: Reusable file listing with selection
- **ButtonGroup**: Manages related buttons with state control

#### Business Logic (`logic/`)
- **FoxgloveLogic**: Foxglove link analysis and launching
- **McapLogic**: MCAP file operations and tool launching
- **NavigationLogic**: Directory navigation with history
- **FileExplorerLogic**: File system operations (existing, enhanced)

#### Utilities (`utils/`)
- **path_utils.py**: Path manipulation and validation
- **utils.py**: File formatting and icons (existing)

### 3. Benefits of New Structure

#### Maintainability
- Each module has a single responsibility
- Easy to find and modify specific functionality
- Clear interfaces between components

#### Testability
- Business logic separated from GUI code
- Individual components can be unit tested
- Mock-friendly architecture

#### Reusability
- GUI components can be reused across different parts of the app
- Business logic modules can be used independently
- Utilities are shared across modules

#### Extensibility
- Easy to add new features without modifying existing code
- New GUI components can be added to the `gui/` package
- New business logic can be added to the `logic/` package

### 4. Migration Path

#### Current State
- `gui_manager.py`: Original monolithic file (keep for reference)
- `main.py`: Original entry point

#### New State
- `gui_manager_refactored.py`: New modular GUI manager
- `main_refactored.py`: New entry point
- Supporting modules in `logic/`, `gui/`, and `utils/`

#### To Switch to New Version
1. Test the new version: `python main_refactored.py`
2. When satisfied, rename files:
   ```bash
   mv gui_manager.py gui_manager_old.py
   mv gui_manager_refactored.py gui_manager.py
   mv main.py main_old.py
   mv main_refactored.py main.py
   ```

### 5. Code Examples

#### Before (Monolithic)
```python
class FoxgloveAppGUIManager:
    def __init__(self):
        # 50+ lines of initialization
        # GUI creation mixed with business logic
        
    def analyze_link(self):
        # 30+ lines mixing URL parsing, file operations, and GUI updates
        
    def create_widgets(self):
        # 200+ lines of GUI creation
```

#### After (Modular)
```python
class FoxgloveAppGUIManager:
    def __init__(self):
        # Initialize business logic modules
        self.foxglove_logic = FoxgloveLogic(self.logic)
        self.mcap_logic = McapLogic(self.logic)
        
        # Initialize GUI components
        self.logger = LoggingComponent(main_frame)
        self.file_list = FileListComponent(parent, on_select=self.on_select)
        
    def analyze_link(self):
        # 10 lines: delegate to business logic, update GUI
        result = self.foxglove_logic.analyze_foxglove_link(link)
        self.update_ui_from_result(result)
```

### 6. Next Steps

1. **Test the refactored version** thoroughly
2. **Add unit tests** for the new modules
3. **Consider further improvements**:
   - Add configuration management
   - Implement plugin architecture
   - Add more comprehensive error handling
   - Consider using dependency injection

### 7. Files to Review

#### Priority 1 (Core New Files)
- `gui_manager_refactored.py` - Main orchestrator
- `logic/foxglove_logic.py` - Foxglove operations
- `logic/mcap_logic.py` - MCAP operations

#### Priority 2 (Supporting Files)
- `gui/logging_component.py` - Logging widget
- `gui/file_list_component.py` - File list widget
- `logic/navigation_logic.py` - Navigation management

#### Priority 3 (Utilities)
- `utils/path_utils.py` - Path utilities
- `gui/button_group.py` - Button management

This modular structure makes the codebase much more maintainable, testable, and extensible while keeping all existing functionality intact.
