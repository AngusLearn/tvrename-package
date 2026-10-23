# tvrename/utils.py
import re
import unicodedata
from pathlib import Path

# Color escape codes (centralized to avoid duplication across modules)
yellow = "\033[33m"
red = "\033[31m"
green = "\033[32m"
cyan = "\033[36m"

yellow_bold = "\033[1;33m"
red_bold = "\033[1;31m"
green_bold = "\033[1;32m"

light_blue = "\033[94m"

reset = "\033[0m"


def sanitize_filename(name):
    """Sanitizes a filename by removing or replacing invalid characters."""
    name = name.replace(".", "﹒")
    name = name.replace(":", "：")
    name = name.replace("?", "？")
    name = name.replace("'", "’")
    name = name.replace("/", "／")
    name = name.replace("!", "！")
    name = name.replace(";", "；")
    name = name.replace("#", "＃")
    return re.sub(r'[<>:"/\\|?*]', '', name)

def truncate_string(string, max_bytes):
    """Truncates a string to a maximum byte length (UTF-8 encoded)."""
    encoded = string.encode('utf-8')
    if len(encoded) > max_bytes:
        return encoded[:max_bytes].decode('utf-8', errors='ignore')
    return string

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

def get_full_extension(filename):
    """Gets the full extension for subtitle files, including language codes."""
    subtitle_exts = ['.ass', '.srt', '.ssa', '.sub', '.vtt', '.smi', '.lrc', '.txt']
    for ext in subtitle_exts:
        if filename.lower().endswith(ext):
            # Check for language code before the extension
            pattern = rf'(\.[a-zA-Z0-9-]+)?{re.escape(ext)}$'
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                lang_part = match.group(1) if match.group(1) else ''
                return lang_part + ext
    # For non-subtitle files, return the standard suffix
    return Path(filename).suffix

def normalize_filename(filename):
    # NFKC normalization converts full-width characters to half-width
    normalized = unicodedata.normalize('NFKC', filename)
    return normalized

