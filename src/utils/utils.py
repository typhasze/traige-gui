import os

from .constants import DEFAULT_FILE_ICON, FILE_ICON_MAP


def format_file_size(size_bytes):
    if size_bytes == 0:
        return "0 B"

    SIZE_NAMES = ("B", "KB", "MB", "GB", "TB")
    UNIT_SIZE = 1024
    i = 0
    size = float(size_bytes)
    while size >= UNIT_SIZE and i < len(SIZE_NAMES) - 1:
        size /= UNIT_SIZE
        i += 1

    if i == 0:
        return f"{int(size)} {SIZE_NAMES[i]}"
    else:
        if size < 10:
            return f"{size:.1f} {SIZE_NAMES[i]}"
        else:
            return f"{size:.0f} {SIZE_NAMES[i]}"


def get_file_icon(filepath):
    """Get an icon for a file based on its extension."""
    ext = os.path.splitext(filepath)[1].lower()
    return FILE_ICON_MAP.get(ext, DEFAULT_FILE_ICON)


def validate_input(input_data):
    return isinstance(input_data, str) and bool(input_data.strip())


def format_output(data):
    if isinstance(data, str):
        return data
    elif data is None:
        return "None"
    elif isinstance(data, (int, float, bool)):
        return str(data)
    else:
        return repr(data)


def log_message(message, level="INFO"):
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def batch_log_messages(messages, level="INFO"):
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for message in messages:
        print(f"[{timestamp}] [{level}] {message}")


def safe_file_operation(operation, *args, **kwargs):
    try:
        result = operation(*args, **kwargs)
        return True, result
    except (OSError, IOError) as e:
        return False, f"File operation error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def efficient_directory_scan(directory_path, extension_filter=None, max_depth=1):
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
