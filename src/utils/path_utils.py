import os
from typing import Tuple

def format_path_for_display(path: str, max_length: int = 50) -> str:
    """Format a path for display, truncating if too long"""
    if len(path) <= max_length:
        return path
    
    # Try to show ...start and end
    if len(path) > max_length:
        start_len = max_length // 2 - 2
        end_len = max_length - start_len - 3
        return f"{path[:start_len]}...{path[-end_len:]}"
    
    return path

def normalize_path(path: str) -> str:
    """Normalize a path (expand user, resolve, etc.)"""
    return os.path.abspath(os.path.expanduser(path))

def get_relative_path(path: str, base_path: str) -> str:
    """Get relative path from base_path to path"""
    try:
        return os.path.relpath(path, base_path)
    except ValueError:
        return path

def ensure_directory_exists(path: str) -> bool:
    """Ensure a directory exists, create if it doesn't"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except (OSError, PermissionError):
        return False

def is_subdirectory(path: str, parent: str) -> bool:
    """Check if path is a subdirectory of parent"""
    try:
        path = os.path.abspath(path)
        parent = os.path.abspath(parent)
        return path.startswith(parent + os.sep) or path == parent
    except (OSError, ValueError):
        return False

def get_common_parent(paths) -> str:
    """Get the common parent directory of multiple paths"""
    if not paths:
        return ""
    
    if len(paths) == 1:
        return os.path.dirname(paths[0])
    
    return os.path.commonpath(paths)

def split_path_components(path: str) -> list:
    """Split a path into its components"""
    components = []
    while True:
        path, tail = os.path.split(path)
        if tail:
            components.append(tail)
        else:
            if path:
                components.append(path)
            break
    components.reverse()
    return components
