"""
Common file operation utilities.

This module provides cross-platform file operations like opening files
and directories using system default applications.
"""

import os
import platform
import subprocess
from typing import Tuple


def open_file_with_default_app(file_path: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Open a file using the system default application.

    Args:
        file_path: Path to the file to open
        timeout: Timeout in seconds for the operation

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        system = platform.system()
        if system == "Linux":
            subprocess.run(["xdg-open", file_path], check=True, timeout=timeout)
        elif system == "Darwin":
            subprocess.run(["open", file_path], check=True, timeout=timeout)
        elif system == "Windows":
            os.startfile(file_path)
        else:
            return False, f"Unsupported system: {system}"
        return True, f"Opened file: {os.path.basename(file_path)}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout opening file: {os.path.basename(file_path)}"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to open file: {e}"
    except Exception as e:
        return False, f"Error opening file: {e}"


def open_directory_in_file_manager(dir_path: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Open a directory in the system file manager.

    Args:
        dir_path: Path to the directory to open
        timeout: Timeout in seconds for the operation

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        system = platform.system()
        if system == "Linux":
            subprocess.run(["xdg-open", dir_path], check=True, timeout=timeout)
        elif system == "Darwin":
            subprocess.run(["open", dir_path], check=True, timeout=timeout)
        elif system == "Windows":
            subprocess.run(["explorer", dir_path], check=True, timeout=timeout)
        else:
            return False, f"Unsupported system: {system}"
        return True, f"Opened in file manager: {dir_path}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout opening file manager for: {dir_path}"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to open file manager: {e}"
    except Exception as e:
        return False, f"Error opening file manager: {e}"


def open_url_in_browser(url: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Open a URL in the default web browser.

    Args:
        url: URL to open
        timeout: Timeout in seconds for the operation

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        subprocess.run(["xdg-open", url], check=True, timeout=timeout)
        return True, "Opened URL in browser"
    except subprocess.TimeoutExpired:
        return False, "Timeout launching browser"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to launch browser: {e}"
    except Exception as e:
        return False, f"Error launching browser: {e}"


def safe_file_read(file_path: str, encoding: str = "utf-8") -> Tuple[bool, str, list]:
    """
    Safely read a file and return its lines.

    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)

    Returns:
        Tuple of (success: bool, error_message: str, lines: list)
    """
    try:
        with open(file_path, "r", encoding=encoding) as f:
            lines = f.readlines()
        return True, "", lines
    except FileNotFoundError:
        return False, f"File not found: {file_path}", []
    except PermissionError:
        return False, f"Permission denied: {file_path}", []
    except UnicodeDecodeError as e:
        return False, f"Encoding error: {e}", []
    except Exception as e:
        return False, f"Error reading file: {e}", []


def safe_file_write(file_path: str, content: str, encoding: str = "utf-8") -> Tuple[bool, str]:
    """
    Safely write content to a file with atomic operations.

    Args:
        file_path: Path to the file to write
        content: Content to write
        encoding: File encoding (default: utf-8)

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        # Write to temporary file first for atomic operation
        temp_path = file_path + ".tmp"
        with open(temp_path, "w", encoding=encoding) as f:
            f.write(content)

        # Atomic replace
        os.replace(temp_path, file_path)
        return True, ""
    except PermissionError:
        return False, f"Permission denied: {file_path}"
    except OSError as e:
        return False, f"OS error: {e}"
    except Exception as e:
        return False, f"Error writing file: {e}"
