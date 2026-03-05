# Code Refactoring and Optimization Summary

## ✅ Completed Refactorings

### 1. Centralized Constants Module (`src/utils/constants.py`)

**Problem**: Constants were scattered across multiple files, making maintenance difficult.

**Solution**: Created a centralized `constants.py` module in the `utils/` folder with:
- Path constants (data paths, logging directories, settings file paths)
- Default settings dictionary
- Process names
- File icon mappings
- Performance limits (cache sizes, timeouts)
- UI constants
- File patterns and extensions

**Benefits**:
- Single source of truth for all configuration values
- Easier to update default settings
- Better code organization
- Reduced duplication

**Files Modified**:
- Created: `src/utils/constants.py` (centralized constants)
- Updated: `src/core_logic.py`, `src/utils/utils.py`, `src/logic/file_explorer_logic.py`, `src/ui/components/settings_tab.py`, `src/gui_manager.py`

---

### 2. Extracted Common File Operations (`src/utils/file_operations.py`)

**Problem**: File opening logic was duplicated in multiple places with inconsistent error handling.

**Solution**: Created `file_operations.py` utility module with cross-platform functions:
- `open_file_with_default_app()` - Open files with system default application
- `open_directory_in_file_manager()` - Open directories in file explorer
- `open_url_in_browser()` - Open URLs in default browser
- `safe_file_read()` - Safe file reading with error handling
- `safe_file_write()` - Atomic file writing operations

**Benefits**:
- Eliminated code duplication
- Consistent error handling across the codebase
- Cross-platform compatibility in one place
- Easier to test and maintain

**Files Modified**:
- Created: `src/utils/file_operations.py`
- Updated: `src/logic/file_explorer_logic.py`, `src/core_logic.py`

---

### 3. Improved Settings Management

**Problem**: Settings loading logic was duplicated and contained hardcoded defaults in multiple places.

**Solution**:
- Centralized all default settings in `constants.py`
- Simplified `load_settings()` in `settings_tab.py`
- Made `reset_settings()` use the centralized defaults
- Standardized settings file path using `SETTINGS_FILE_PATH` constant

**Benefits**:
- Eliminated duplicate default settings definitions
- Settings updates now require changes in only one location
- Cleaner, more maintainable code

---

### 4. Process Management Optimization

**Problem**: Magic numbers for timeouts and intervals scattered throughout code.

**Solution**: Extracted to constants:
- `PROCESS_MONITOR_INTERVAL` = 10 seconds
- `LONG_RUNNING_PROCESS_THRESHOLD` = 7200 seconds (2 hours)
- `PROCESS_SHUTDOWN_TIMEOUT` = 2 seconds
- `FILE_INFO_CACHE_SIZE_LIMIT` = 1000 entries

**Benefits**:
- Easy to adjust performance parameters
- Self-documenting code
- Consistent behavior across the application

---

## 🔄 Recommended Future Improvements

### High Priority

#### 1. ✅ Break Down Long Methods in `file_explorer_tab.py` — **DONE**

**What was done**:
- `_build_event_log_viewer_ui()` extracted into 6 focused helper methods
- `load_event_log_data()` extracted into `_preprocess_event_log_lines()` + `_parse_event_rows()`
- `parse_timestamp()` extracted `_normalize_timestamp_str()` + class-level `_TIMESTAMP_FORMATS` constant
- `find_mcap_with_buffer()` extracted `_find_best_mcap_index()`

**Benefits achieved**:
- All public methods now under 30 lines
- Timestamp formats centralised in one class constant
- Extracted helpers are individually testable
- Better separation of concerns throughout

---

#### 2. ✅ Create a Settings Manager Class — **DONE**

**What was done**: Created `src/utils/settings_manager.py` with `SettingsManager`:
- `load()` — merges user file with defaults, handles corrupt/missing files
- `save(updates=None)` — atomic write via temp file + `os.replace()`
- `reset()` — restores all defaults and persists
- `get(key, default)` / `set(key, value)` / `update(dict)` — in-memory access
- `as_dict()` — returns a shallow copy
- `validate_path(key)` — checks a path setting exists and is accessible

`settings_tab.py` now delegates all persistence to `SettingsManager` via `self._manager`.

**Benefits achieved**:
- Single source of persistence logic (no more duplicate JSON read/write)
- Atomic saves prevent file corruption
- Fully testable without a GUI

---

#### 3. ✅ Add Logging Framework — **DONE**

**What was done**: Created `src/utils/logger.py` with:
- `setup_logging()` — configures root `traige_gui` logger with rotating file handler
  (5 MB × 3 files in `~/.traige_gui/logs/`) and WARNING-level console handler
- `get_logger(name)` — returns a named child logger for any module
- `TkinterLogHandler` — custom `logging.Handler` that writes records to a `tk.Text`
  widget (supports `set_clear_pending()` for the `clear_first` use-case)

**Integration**:
- `main.py` calls `setup_logging()` before any imports
- `gui_manager.log_message()` routes through `logger.info/error()` → `TkinterLogHandler` → widget
- `core.py` background thread uses `logger.error/warning()` directly (thread-safe)
- `settings_tab.py`, `file_explorer_tab.py`, `core.py` all have `logger = get_logger(__name__)`

**Benefits achieved**:
- All log output persisted to rotating file for post-mortem debugging
- Structured log levels (DEBUG/INFO/WARNING/ERROR)
- Background threads log safely without crossing Tkinter thread boundary
- Industry-standard approach — ready for future structured log sinks

---

### Medium Priority

#### 4. Add Type Hints Throughout Codebase

**Current State**: Partial type hints in some files.

**Recommendation**: Add complete type hints to all functions:
```python
def get_file_info(self, path: str) -> Dict[str, Any]:
    """Get file information with caching."""
    ...

def open_file(self, file_path: str) -> Tuple[bool, str]:
    """Open a file using system default application."""
    ...
```

**Benefits**:
- Better IDE autocomplete
- Catch errors earlier with mypy
- Self-documenting code

---

#### 5. Extract Event Log Viewer to Separate Component

**Current State**: Event log viewer UI logic embedded in `FileExplorerTab`.

**Recommendation**: Create `src/ui/components/event_log_viewer.py`:
```python
class EventLogViewer:
    def __init__(self, parent, file_path, on_close_callback):
        self.parent = parent
        self.file_path = file_path
        self.on_close_callback = on_close_callback
        self.build_ui()

    def build_ui(self):
        """Build the event log viewer interface"""

    def load_events(self) -> List[Tuple]:
        """Parse and load event log data"""

    def filter_events(self, search_text: str):
        """Filter events based on search text"""
```

**Benefits**:
- Separation of concerns
- Reusable component
- Easier testing
- Cleaner file_explorer_tab.py

---

#### 6. Add Unit Tests

**Current State**: No automated tests.

**Recommendation**: Add pytest-based tests:
```
tests/
├── test_constants.py
├── test_file_operations.py
├── test_file_explorer_logic.py
├── test_settings_manager.py
└── test_utils.py
```

**Benefits**:
- Catch regressions early
- Safer refactoring
- Documentation through examples
- Better code quality

---

### Low Priority

#### 7. Use Dataclasses for Data Structures

**Recommendation**: Replace dictionaries with dataclasses:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProcessInfo:
    process: subprocess.Popen
    name: str
    start_time: float
    id: int

@dataclass
class FileInfo:
    size: int
    mtime: float
    icon: str
    size_str: str
```

**Benefits**:
- Type safety
- Auto-generated `__init__`, `__repr__`
- Better IDE support

---

#### 8. Add Configuration Validation

**Recommendation**: Validate settings on load:
```python
from typing import TypedDict, Required

class Settings(TypedDict, total=False):
    bazel_working_dir: Required[str]
    nas_dir: Required[str]
    max_foxglove_files: int
    bazel_bag_gui_rate: float

def validate_settings(settings: dict) -> Tuple[bool, str]:
    """Validate settings structure and values"""
    # Check required fields
    # Validate types
    # Check path existence
    # Validate ranges (e.g., rate > 0)
```

---

## 📊 Performance Improvements

### Already Implemented
1. **File Info Caching**: 1000-entry cache for file metadata
2. **Process Health Monitoring**: Background thread checks every 10 seconds
3. **Atomic File Writes**: Prevent file corruption during saves

### Potential Future Optimizations
1. **Lazy Loading**: Load directory contents on-demand
2. **Thread Pools**: Parallelize file operations for large directories
3. **Database for History**: SQLite for navigation history instead of in-memory list
4. **Memoization**: Cache frequently called functions like path validation

---

## 📈 Code Quality Metrics

### Before Refactoring
- Constants scattered across 5+ files
- Duplicate file operation code in 3 places
- Settings logic in 2 separate locations
- Magic numbers throughout codebase

### After Refactoring
- All constants in 1 centralized module
- File operations in dedicated utility module
- Consistent use of constants throughout
- Improved code organization and readability

### Future Target
- 80%+ test coverage
- Full type hint coverage
- Methods under 50 lines
- Cyclomatic complexity under 10
- Clear separation of concerns

---

## 🚀 Quick Wins

These can be implemented quickly with high impact:

1. **Add docstrings to all public methods** (1-2 hours)
2. **Replace magic strings with constants** (1 hour)
3. **Add input validation to public methods** (2-3 hours)
4. **Create SettingsManager class** (3-4 hours)
5. **Add basic unit tests for utilities** (4-6 hours)

---

## 📝 Notes

- All refactorings maintain backward compatibility
- No breaking changes to existing functionality
- Settings file format unchanged
- Process managementlogic preserved
- UI behavior identical

---

## 🔗 Related Documentation

- [Architecture v2](../architecture_v2.md) - System architecture overview
- [README](../README.md) - User documentation
- [Constants Module](../src/constants.py) - Centralized constants
- [File Operations](../src/utils/file_operations.py) - Common file utilities

---

**Last Updated**: March 5, 2026
**Author**: Code Refactoring Session
**Status**: Active Development
