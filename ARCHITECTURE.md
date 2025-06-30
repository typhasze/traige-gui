# Foxglove MCAP Launcher - Modular Architecture

## Overview
The application has been refactored from a monolithic structure to a modular architecture with clear separation of concerns. This makes the codebase more maintainable, testable, and easier to extend.

## Architecture

### 🏗️ Directory Structure
```
src/
├── gui/                          # GUI components and UI logic
│   ├── components/               # Reusable UI components
│   │   ├── foxglove_tab.py      # Foxglove tab component
│   │   ├── explorer_tab.py      # File explorer tab component
│   │   └── __init__.py
│   ├── logging_component.py     # Logging widget component
│   └── __init__.py
├── logic/                       # Business logic modules
│   ├── file_explorer_logic.py   # File system operations
│   ├── foxglove_logic.py        # Foxglove and process management
│   ├── mcap_logic.py            # MCAP file handling
│   ├── navigation_logic.py      # Navigation and history management
│   └── __init__.py
├── utils/                       # Utility functions
│   ├── utils.py                 # File utilities (size formatting, icons)
│   ├── path_utils.py            # Path manipulation utilities
│   └── __init__.py
├── gui_manager.py               # Original GUI manager (legacy)
├── gui_manager_modular.py       # New modular GUI manager
├── core_logic.py                # Legacy compatibility layer
└── main.py                      # Application entry point
```

## 🧩 Modules

### Logic Layer (`logic/`)

#### `foxglove_logic.py`
- **Purpose**: Process management and Foxglove operations
- **Key Features**:
  - Launch/terminate Foxglove Studio
  - Launch/terminate Bazel tools (bag GUI, viz)
  - Process lifecycle management
  - Symlink-based multi-file handling
- **Methods**:
  - `launch_foxglove(mcap_filepath)`
  - `launch_bazel_bag_gui(mcap_path)`
  - `launch_bazel_tools_viz()`
  - `play_bazel_bag_gui_with_symlinks(mcap_files)`
  - `terminate_all_processes()`

#### `mcap_logic.py`
- **Purpose**: MCAP file operations and URL parsing
- **Key Features**:
  - Parse Foxglove URLs to extract MCAP paths
  - List and manage MCAP files
  - Handle local/remote path mapping
  - Directory structure navigation
- **Methods**:
  - `extract_mcap_details_from_foxglove_link(link)`
  - `list_mcap_files(directory)`
  - `get_local_folder_path(remote_path)`
  - `list_default_subfolders()`
  - `find_parent_default_folder(path)`

#### `file_explorer_logic.py`
- **Purpose**: File system operations and explorer functionality
- **Key Features**:
  - Directory listing and navigation
  - File type detection and icons
  - System integration (open files, file manager)
  - Clipboard operations
  - Button state management
- **Methods**:
  - `list_directory(path)`
  - `get_file_info(path)`
  - `open_file(path)`
  - `open_in_file_manager(path)`
  - `copy_to_clipboard(root, text)`
  - `get_file_action_states(path, is_parent_dir)`

#### `navigation_logic.py`
- **Purpose**: Navigation history and path management
- **Key Features**:
  - Navigation history tracking
  - Path validation and normalization
  - Breadcrumb navigation
- **Methods**:
  - `add_to_history(path)`
  - `get_previous_path()`
  - `clear_history()`
  - `get_history()`

### GUI Layer (`gui/`)

#### `logging_component.py`
- **Purpose**: Centralized logging UI component
- **Key Features**:
  - Colored log messages (info/error)
  - Scrollable text widget
  - Message formatting and timestamps
- **Methods**:
  - `create_log_widget(parent)`
  - `log_message(message, is_error, clear_first)`

#### `components/` (Planned)
- **Purpose**: Reusable UI components for tabs
- **Benefits**:
  - Encapsulated UI logic
  - Easier testing and maintenance
  - Consistent styling and behavior

### Utilities Layer (`utils/`)

#### `utils.py`
- **Purpose**: General utility functions
- **Key Features**:
  - File size formatting
  - File type icon selection
  - Common file operations
- **Methods**:
  - `format_file_size(bytes)`
  - `get_file_icon(filepath)`

#### `path_utils.py`
- **Purpose**: Path manipulation utilities
- **Key Features**:
  - Path normalization
  - Cross-platform path handling
  - Path validation
- **Methods**:
  - `normalize_path(path)`
  - `is_valid_path(path)`
  - `get_relative_path(base, target)`

## 🔄 Migration Strategy

### Backward Compatibility
The refactoring maintains backward compatibility through:

1. **`core_logic.py`**: Acts as a compatibility layer that delegates to modular components
2. **`gui_manager.py`**: Original implementation remains functional
3. **Gradual Migration**: New features can use modular components while legacy code continues to work

### Benefits of Modular Architecture

#### 🧪 **Testability**
- Each module can be unit tested independently
- Mocked dependencies for isolated testing
- Clear interfaces between components

#### 🔧 **Maintainability**
- Single responsibility principle
- Easier to locate and fix bugs
- Reduced code duplication

#### 🚀 **Extensibility**
- Easy to add new features without affecting existing code
- Plugin-like architecture for new file types or tools
- Configurable components

#### 📖 **Readability**
- Smaller, focused modules
- Clear separation of concerns
- Self-documenting code structure

## 🎯 Usage Examples

### Using Modular Components
```python
# Initialize components
foxglove_logic = FoxgloveLogic()
mcap_logic = McapLogic()
file_explorer_logic = FileExplorerLogic()

# Extract MCAP details from URL
folder, filename = mcap_logic.extract_mcap_details_from_foxglove_link(url)

# Launch Foxglove
message, error = foxglove_logic.launch_foxglove(mcap_path)

# Get file info
file_info = file_explorer_logic.get_file_info(file_path)

# Determine button states
states = file_explorer_logic.get_file_action_states(selected_path)
```

### Creating New Features
```python
# Add a new logic module
from logic.new_feature_logic import NewFeatureLogic

# Extend existing components
class ExtendedMcapLogic(McapLogic):
    def new_mcap_operation(self):
        # New functionality
        pass
```

## 🚧 Future Improvements

1. **Complete GUI Component Extraction**: Move remaining UI logic into `gui/components/`
2. **Configuration Management**: Add a config module for application settings
3. **Plugin System**: Allow loading external modules for custom file types
4. **Event System**: Implement pub-sub pattern for component communication
5. **Async Operations**: Add async support for long-running operations
6. **Testing Suite**: Comprehensive unit and integration tests
7. **Documentation**: Auto-generated API documentation

## 📝 Migration Checklist

- [x] Extract file explorer logic
- [x] Extract MCAP handling logic  
- [x] Extract Foxglove process management
- [x] Extract navigation logic
- [x] Extract logging component
- [x] Extract utility functions
- [x] Create compatibility layer
- [ ] Extract GUI tab components
- [ ] Add comprehensive tests
- [ ] Update documentation
- [ ] Performance optimization
- [ ] Add configuration management

This modular architecture provides a solid foundation for future development while maintaining the existing functionality and user experience.
