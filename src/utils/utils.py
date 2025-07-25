import os
import shutil
import tempfile
import subprocess

# File extension to icon mapping for better performance
FILE_ICON_MAP = {
    '.mcap': "🎥",
    '.txt': "📄", '.log': "📄", '.md': "📄",
    '.py': "📜", '.js': "📜", '.cpp': "📜", '.h': "📜", '.c': "📜", '.java': "📜",
    '.jpg': "🖼️", '.png': "🖼️", '.gif': "🖼️", '.bmp': "🖼️", '.jpeg': "🖼️",
    '.zip': "📦", '.tar': "📦", '.gz': "📦", '.rar': "📦",
    '.pdf': "📕",
    '.json': "⚙️", '.xml': "⚙️", '.yaml': "⚙️", '.yml': "⚙️"
}

def format_file_size(size_bytes):
    """
    Format file size with appropriate units (B, KB, MB, GB, TB).
    Optimized for performance with fewer function calls.
    """
    if size_bytes == 0:
        return "0 B"
    
    # Use constants for better performance
    SIZE_NAMES = ("B", "KB", "MB", "GB", "TB")
    UNIT_SIZE = 1024
    
    # More efficient calculation without multiple function calls
    i = 0
    size = float(size_bytes)
    while size >= UNIT_SIZE and i < len(SIZE_NAMES) - 1:
        size /= UNIT_SIZE
        i += 1
    
    # Format with appropriate precision
    if i == 0:
        return f"{int(size)} {SIZE_NAMES[i]}"
    else:
        # Use conditional logic to determine format specifier
        if size < 10:
            return f"{size:.1f} {SIZE_NAMES[i]}"
        else:
            return f"{size:.0f} {SIZE_NAMES[i]}"

def get_file_icon(filepath):
    """
    Get file icon based on extension using optimized lookup.
    """
    ext = os.path.splitext(filepath)[1].lower()
    return FILE_ICON_MAP.get(ext, "📄")

def validate_input(input_data):
    """
    Validates the input data for the application.

    Args:
        input_data (str): The input data to validate.

    Returns:
        bool: True if the input is valid, False otherwise.
    """
    # Optimized validation: check type and content in one go
    return isinstance(input_data, str) and bool(input_data.strip())

def format_output(data):
    """
    Formats the output data for display.

    Args:
        data (any): The data to format.

    Returns:
        str: The formatted string representation of the data.
    """
    # Optimize string conversion for better performance
    if isinstance(data, str):
        return data
    elif data is None:
        return "None"
    elif isinstance(data, (int, float, bool)):
        return str(data)
    else:
        # For complex objects, use repr for better debugging
        return repr(data)

def log_message(message, level="INFO"):
    """
    Logs a message to the console or a log file with improved formatting.

    Args:
        message (str): The message to log.
        level (str): The log level (INFO, WARNING, ERROR, DEBUG).
    """
    import datetime
    
    # More informative logging with timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def batch_log_messages(messages, level="INFO"):
    """
    Log multiple messages efficiently to reduce I/O overhead.
    
    Args:
        messages (list): List of messages to log.
        level (str): The log level for all messages.
    """
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for message in messages:
        print(f"[{timestamp}] [{level}] {message}")

def safe_file_operation(operation, *args, **kwargs):
    """
    Safely execute file operations with error handling.
    
    Args:
        operation: The file operation function to execute.
        *args: Arguments for the operation.
        **kwargs: Keyword arguments for the operation.
        
    Returns:
        tuple: (success: bool, result_or_error_message: str)
    """
    try:
        result = operation(*args, **kwargs)
        return True, result
    except (OSError, IOError) as e:
        return False, f"File operation error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"

def efficient_directory_scan(directory_path, extension_filter=None, max_depth=1):
    """
    Efficiently scan directory with optional filtering and depth control.
    
    Args:
        directory_path (str): Path to scan.
        extension_filter (str, optional): File extension to filter by.
        max_depth (int): Maximum depth to scan.
        
    Returns:
        tuple: (files: list, directories: list, error: str or None)
    """
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
