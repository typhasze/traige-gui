import os
from ..utils.utils import format_file_size, get_file_icon

class FileExplorerLogic:
    def __init__(self, base_path=None):
        self.base_path = base_path or os.path.expanduser('~/data')

    def list_directory(self, path, show_hidden=False):
        """Return (dirs, files) in the given path."""
        if not os.path.isdir(path):
            return [], []
        items = os.listdir(path)
        dirs, files = [], []
        for item in items:
            if not show_hidden and item.startswith('.'):
                continue
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                dirs.append(item)
            else:
                files.append(item)
        return sorted(dirs, key=str.lower), sorted(files, key=str.lower)

    def is_mcap_file(self, filename):
        return filename.lower().endswith('.mcap')

    def get_file_info(self, path):
        """Return dict with size, mtime, icon, etc."""
        try:
            size = os.path.getsize(path)
            mtime = os.path.getmtime(path)
            icon = get_file_icon(path)
            size_str = format_file_size(size)
            return {'size': size, 'mtime': mtime, 'icon': icon, 'size_str': size_str}
        except Exception:
            return {'size': None, 'mtime': None, 'icon': get_file_icon(path), 'size_str': 'N/A'}

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
