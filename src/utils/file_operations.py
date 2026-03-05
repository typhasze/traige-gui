"""Common file operation utilities for opening files, directories, and URLs."""

import os
import platform
import subprocess
from typing import Tuple


def _run_open_cmd(cmd: list, path: str, timeout: int) -> Tuple[bool, str]:
    """Run a subprocess open command; return (success, error_message)."""
    try:
        subprocess.run(cmd, check=True, timeout=timeout)
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"Timeout opening: {os.path.basename(path)}"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to open: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def open_file_with_default_app(file_path: str, timeout: int = 10) -> Tuple[bool, str]:
    """Open a file using the system default application."""
    system = platform.system()
    if system == "Windows":
        try:
            os.startfile(file_path)
            return True, f"Opened file: {os.path.basename(file_path)}"
        except Exception as e:
            return False, f"Error opening file: {e}"
    cmd_name = "xdg-open" if system == "Linux" else "open" if system == "Darwin" else None
    if cmd_name is None:
        return False, f"Unsupported system: {system}"
    ok, err = _run_open_cmd([cmd_name, file_path], file_path, timeout)
    return (True, f"Opened file: {os.path.basename(file_path)}") if ok else (False, err)


def open_directory_in_file_manager(dir_path: str, timeout: int = 10) -> Tuple[bool, str]:
    """Open a directory in the system file manager."""
    system = platform.system()
    cmd_map = {"Linux": "xdg-open", "Darwin": "open", "Windows": "explorer"}
    if system not in cmd_map:
        return False, f"Unsupported system: {system}"
    ok, err = _run_open_cmd([cmd_map[system], dir_path], dir_path, timeout)
    return (True, f"Opened in file manager: {dir_path}") if ok else (False, err)


def open_url_in_browser(url: str, timeout: int = 10) -> Tuple[bool, str]:
    """Open a URL with xdg-open (Linux)."""
    ok, err = _run_open_cmd(["xdg-open", url], url, timeout)
    return (True, "Opened URL in browser") if ok else (False, err)


def safe_file_read(file_path: str, encoding: str = "utf-8") -> Tuple[bool, str, list]:
    """Safely read a file and return its lines."""
    try:
        with open(file_path, "r", encoding=encoding) as f:
            return True, "", f.readlines()
    except FileNotFoundError:
        return False, f"File not found: {file_path}", []
    except PermissionError:
        return False, f"Permission denied: {file_path}", []
    except UnicodeDecodeError as e:
        return False, f"Encoding error: {e}", []
    except Exception as e:
        return False, f"Error reading file: {e}", []


def safe_file_write(file_path: str, content: str, encoding: str = "utf-8") -> Tuple[bool, str]:
    """Safely write content to a file atomically."""
    try:
        temp_path = file_path + ".tmp"
        with open(temp_path, "w", encoding=encoding) as f:
            f.write(content)
        os.replace(temp_path, file_path)
        return True, ""
    except PermissionError:
        return False, f"Permission denied: {file_path}"
    except OSError as e:
        return False, f"OS error: {e}"
    except Exception as e:
        return False, f"Error writing file: {e}"
