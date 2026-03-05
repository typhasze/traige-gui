import os
from typing import List, Optional, Tuple

from .constants import DEFAULT_FILE_ICON, FILE_ICON_MAP


def format_file_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    SIZE_NAMES = ("B", "KB", "MB", "GB", "TB")
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(SIZE_NAMES) - 1:
        size /= 1024
        i += 1
    if i == 0:
        return f"{int(size)} {SIZE_NAMES[i]}"
    return f"{size:.1f} {SIZE_NAMES[i]}" if size < 10 else f"{size:.0f} {SIZE_NAMES[i]}"


def get_file_icon(filepath: str) -> str:
    """Get an icon for a file based on its extension."""
    ext = os.path.splitext(filepath)[1].lower()
    return FILE_ICON_MAP.get(ext, DEFAULT_FILE_ICON)


def efficient_directory_scan(
    directory_path: str,
    extension_filter: Optional[str] = None,
    max_depth: int = 1,
) -> Tuple[List[str], List[str], Optional[str]]:
    if not os.path.isdir(directory_path):
        return [], [], f"Invalid directory: {directory_path}"

    files, directories = [], []
    try:
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            if os.path.isdir(item_path):
                directories.append(item)
            elif os.path.isfile(item_path):
                if extension_filter is None or item.lower().endswith(extension_filter.lower()):
                    files.append(item)
        return sorted(files), sorted(directories), None
    except (PermissionError, OSError) as e:
        return [], [], f"Access error: {e}"
