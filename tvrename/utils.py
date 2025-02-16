# tvrename/utils.py
import re

def sanitize_filename(name):
    """Sanitizes a filename by removing or replacing invalid characters."""
    name = name.replace("'", "’")
    name = name.replace("/", "／")
    return re.sub(r'[<>:"/\\|?*]', '', name)

def truncate_string(string, length):
    """Truncates a string to a specified length."""
    return string[:length] if len(string) > length else string

def apply_truncation(format_string, placeholder, value):
    """Applies truncation based on `.take({length})` syntax."""
    match = re.search(rf"\{{{placeholder}\.take\((\d+)\)\}}", format_string)
    if match:
        length = int(match.group(1))
        return format_string.replace(f"{{{placeholder}.take({length})}}", truncate_string(value, length))
    return format_string.replace(f"{{{placeholder}}}", value)

def extract_from_folder_name(folder_name):
    """Extracts TMDb ID or series name from folder name."""
    tmdb_id_match = re.search(r"\[tmdbid-(\d+)\]", folder_name, re.IGNORECASE)
    if tmdb_id_match:
        return tmdb_id_match.group(1), None
    return None, folder_name