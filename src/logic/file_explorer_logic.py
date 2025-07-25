import os
import platform
import subprocess
from functools import lru_cache
from typing import Tuple, List, Dict, Optional, Any
from ..utils.utils import format_file_size, get_file_icon

class FileExplorerLogic:
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.path.expanduser('~/data')
        # Cache for file info to improve performance
        self._file_info_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_size_limit = 1000

    def _clear_cache_if_needed(self) -> None:
        """Clear cache if it gets too large to prevent memory issues."""
        if len(self._file_info_cache) > self._cache_size_limit:
            self._file_info_cache.clear()

    def list_directory(self, path: str, show_hidden: bool = False) -> Tuple[List[str], List[str]]:
        """
        Return (dirs, files) in the given path.
        Optimized for performance with better error handling.
        """
        from ..utils.utils import efficient_directory_scan
        
        # Use the optimized directory scan utility
        files, directories, error = efficient_directory_scan(path)
        
        if error:
            return [], []
        
        # Apply hidden file filter if needed
        if not show_hidden:
            files = [f for f in files if not f.startswith('.')]
            directories = [d for d in directories if not d.startswith('.')]
        
        return directories, files

    def is_mcap_file(self, filename):
        """Check if filename is an MCAP file - optimized for performance."""
        return filename.lower().endswith('.mcap')

    def get_file_info(self, path):
        """
        Return dict with size, mtime, icon, etc.
        Uses caching for better performance on repeated calls.
        """
        # Check cache first
        if path in self._file_info_cache:
            stat_result = os.stat(path)
            cached_info = self._file_info_cache[path]
            # Check if file has been modified since caching
            if cached_info.get('mtime') == stat_result.st_mtime:
                return cached_info
        
        try:
            stat_result = os.stat(path)
            size = stat_result.st_size
            mtime = stat_result.st_mtime
            icon = get_file_icon(path)
            size_str = format_file_size(size)
            
            info = {
                'size': size,
                'mtime': mtime,
                'icon': icon,
                'size_str': size_str
            }
            
            # Cache the result
            self._clear_cache_if_needed()
            self._file_info_cache[path] = info
            return info
            
        except (OSError, IOError):
            # Return default info for inaccessible files
            return {
                'size': None,
                'mtime': None,
                'icon': get_file_icon(path),
                'size_str': 'N/A'
            }

    def open_file(self, file_path):
        """Open a file using the system default application. Returns (success, message)."""
        import platform
        import subprocess
        import os
        try:
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdg-open", file_path], check=True)
            elif system == "Darwin":
                subprocess.run(["open", file_path], check=True)
            elif system == "Windows":
                os.startfile(file_path)
            else:
                return False, f"Unsupported system: {system}"
            return True, f"Opened file: {os.path.basename(file_path)}"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to open file: {e}"
        except Exception as e:
            return False, f"Error opening file: {e}"

    def open_in_file_manager(self, dir_path):
        """Open a directory in the system file manager. Returns (success, message)."""
        import platform
        import subprocess
        import os
        try:
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdg-open", dir_path], check=True)
            elif system == "Darwin":
                subprocess.run(["open", dir_path], check=True)
            elif system == "Windows":
                subprocess.run(["explorer", dir_path], check=True)
            else:
                return False, f"Unsupported system: {system}"
            return True, f"Opened in file manager: {dir_path}"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to open file manager: {e}"
        except Exception as e:
            return False, f"Error opening file manager: {e}"

    def copy_to_clipboard(self, root, text):
        """Copy text to clipboard using the Tk root. Returns (success, message)."""
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            return True, f"Copied to clipboard: {text}"
        except Exception as e:
            return False, f"Error copying to clipboard: {e}"

    def get_file_action_states(self, selected_paths, is_multiple_selection):
        """
        Given a list of paths, return a dict of which file action buttons should be enabled.
        """
        states = {
            "open_file": False,
            "copy_path": False,
            "open_with_foxglove": False,
            "open_with_bazel": False
        }

        if not selected_paths:
            return states

        # Logic for single selection
        if not is_multiple_selection:
            item_path = selected_paths[0]
            states["copy_path"] = True
            if os.path.isfile(item_path):
                is_mcap = self.is_mcap_file(item_path)
                states["open_file"] = not is_mcap  # Only enable for non-mcap files
                if is_mcap:
                    states["open_with_foxglove"] = True
                    states["open_with_bazel"] = True
        
        # Logic for multiple selections (or single)
        are_all_mcap = all(self.is_mcap_file(p) and os.path.isfile(p) for p in selected_paths)
        if are_all_mcap:
            states["open_with_bazel"] = True

        return states
