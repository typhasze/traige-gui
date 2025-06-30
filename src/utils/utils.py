import os
import math
import shutil
import tempfile
import subprocess

def format_file_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_file_icon(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.mcap':
        return "🎥"
    elif ext in ['.txt', '.log', '.md']:
        return "📄"
    elif ext in ['.py', '.js', '.cpp', '.h', '.c', '.java']:
        return "📜"
    elif ext in ['.jpg', '.png', '.gif', '.bmp', '.jpeg']:
        return "🖼️"
    elif ext in ['.zip', '.tar', '.gz', '.rar']:
        return "📦"
    elif ext == '.pdf':
        return "📕"
    elif ext in ['.json', '.xml', '.yaml', '.yml']:
        return "⚙️"
    else:
        return "📄"

def validate_input(input_data):
    """
    Validates the input data for the application.

    Args:
        input_data (str): The input data to validate.

    Returns:
        bool: True if the input is valid, False otherwise.
    """
    # Example validation: check if input is not empty
    return bool(input_data.strip())

def format_output(data):
    """
    Formats the output data for display.

    Args:
        data (any): The data to format.

    Returns:
        str: The formatted string representation of the data.
    """
    # Example formatting: convert data to string
    return str(data)

def log_message(message):
    """
    Logs a message to the console or a log file.

    Args:
        message (str): The message to log.
    """
    print(f"[LOG] {message}")  # Simple console logging; can be expanded to file logging if needed.
