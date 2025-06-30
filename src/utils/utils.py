import os
import math

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
