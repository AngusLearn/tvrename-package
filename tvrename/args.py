# tvrename/args.py
import argparse

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Rename and organize series files.")
    parser.add_argument("--q", help="TMDb ID or series title to search for.")
    parser.add_argument("--input", nargs='+', help="Path to the input directory or file (supports wildcards).  Accepts multiple patterns.", default=["."])
    parser.add_argument("--format", help="Custom format for renaming files.")
    parser.add_argument("--lang", default="ja-JP", help="Language for TMDb data (default: ja-JP).")
    parser.add_argument("--season", type=int, help="Process only a specific season (default: all).")
    parser.add_argument("--output", help="Output directory for renamed files.")
    parser.add_argument("--action", choices=["dry-run", "rename", "copy"], default="dry-run", help="Action to perform (default: dry-run).")
    parser.add_argument("-r", "--recursive", action="store_true", help="Process files recursively in the input directory.")
    return parser.parse_args()
