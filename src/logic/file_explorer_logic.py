import os
from utils.utils import format_file_size, get_file_icon

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

    def _run_subprocess(self, cmd, path, is_file=True):
        """Helper to run a subprocess for opening files or directories."""
        import platform
        import subprocess
        import os
        try:
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdg-open", path], check=True)
            elif system == "Darwin":
                subprocess.run(["open", path], check=True)
            elif system == "Windows":
                if is_file and hasattr(os, 'startfile'):
                    os.startfile(path)
                else:
                    subprocess.run(["explorer", path], check=True)
            else:
                return False, f"Unsupported system: {system}"
            return True, f"Opened {'file' if is_file else 'in file manager'}: {os.path.basename(path) if is_file else path}"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to open {'file' if is_file else 'file manager'}: {e}"
        except Exception as e:
            return False, f"Error opening {'file' if is_file else 'file manager'}: {e}"

    def open_file(self, file_path):
        """Open a file using the system default application. Returns (success, message)."""
        return self._run_subprocess(None, file_path, is_file=True)

    def open_in_file_manager(self, dir_path):
        """Open a directory in the system file manager. Returns (success, message)."""
        return self._run_subprocess(None, dir_path, is_file=False)

    def copy_to_clipboard(self, root, text):
        """Copy text to clipboard using the Tk root. Returns (success, message)."""
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            return True, f"Copied to clipboard: {text}"
        except Exception as e:
            return False, f"Error copying to clipboard: {e}"

    def get_file_action_states(self, item_path, is_parent_dir=False):
        """
        Given a path, return a dict of which file action buttons should be enabled.
        If is_parent_dir is True, disables all actions.
        """
        states = {
            "open_file": False,
            "copy_path": False,
            "open_with_foxglove": False,
            "open_with_bazel": False
        }
        if is_parent_dir:
            return states
        if not os.path.exists(item_path):
            return states
        if os.path.isfile(item_path):
            states["open_file"] = True
            states["copy_path"] = True
            if self.is_mcap_file(item_path):
                states["open_with_foxglove"] = True
                states["open_with_bazel"] = True
        elif os.path.isdir(item_path):
            states["copy_path"] = True
        return states
