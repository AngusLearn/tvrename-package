#!/usr/bin/env python3
# tvrename/main.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from colorama import init
from glob import glob

from .args import parse_arguments
from .config import load_config
from .core import fetch_series_details, process_file, _perform_action
from .utils import sanitize_filename, extract_from_folder_name, yellow, red, yellow_bold, red_bold, green_bold, reset
import requests




# Initialize colorama
init(autoreset=True)

# Default path based on OS
if os.name == 'nt':
    default_env_path = "C:\\tvrename\\.env"
else:
    default_env_path = "/etc/tvrename/.env"

dotenv_path = os.getenv("DOTENV_PATH", default_env_path)

if Path(dotenv_path).exists():
    load_dotenv(dotenv_path=dotenv_path)

API_KEY = os.getenv("API_KEY")


def _get_destin_display(file, final_output_path, output_path):
    """Gets source and destination display names for output messages."""
    if str(Path(final_output_path).parent) == str(Path(file).parent):
        destin_file_name = str(Path(final_output_path).relative_to(output_path if output_path else file.parent))
        source_file_name = str(Path(file).relative_to(output_path if output_path else file.parent))
    else:
        destin_file_name = final_output_path
        source_file_name = file
    return source_file_name, destin_file_name


def _perform_rename(file, final_output_path, args, action):
    """Performs a single rename/copy/hardlink operation and returns status."""
    source_file_name, destin_file_name = _get_destin_display(file, final_output_path, args.output)
    return action(file, final_output_path, source_file_name, destin_file_name, args)


def main():
    """Main function to run the tvrename script."""
    global API_KEY

    args = parse_arguments()

    # Validate API key
    if not API_KEY:
        print(f"{red_bold}Error: API_KEY not found in environment variables{reset}")
        print(f"Please ensure your API key is set in {dotenv_path}")
        sys.exit(1)

    # Collect files from all input patterns
    files = []
    for input_pattern in args.input:
        input_path_str = input_pattern
        input_path = Path(input_path_str).resolve()

        if '*' in input_path_str:
            base_dir = Path(os.path.dirname(input_path_str)).resolve()
            if not base_dir.exists():
                print(f"Error: The specified input path does not exist: {base_dir}")
                continue
            found_files = [Path(f).resolve() for f in glob(input_path_str)]
            if not found_files:
                print(f"Warning: No files found matching the wildcard: {input_path_str}")
                continue
            files.extend(found_files)
        else:
            if not input_path.exists():
                print(f"Error: The specified input path does not exist: {input_path}")
                continue
            if input_path.is_file():
                files.append(input_path)
            else:
                if args.recursive:
                    files.extend([f for f in input_path.rglob("*") if f.is_file()])
                else:
                    files.extend([f for f in input_path.iterdir() if f.is_file()])

    if not files:
        print("Error: No files found based on the provided input patterns.")
        sys.exit(1)

    output_path = Path(args.output).resolve() if args.output else None

    # Load configuration
    config_path = None
    for input_pattern in args.input:
        input_path = Path(input_pattern).resolve()
        if input_path.is_dir():
            config_files = list(input_path.glob("**/.config"))
            if config_files:
                config_path = config_files[0]
                break
    if not config_path:
        config_path = Path(".") / ".config"
    episode_shift = load_config(config_path)

    # Determine current folder name
    if args.input and args.input != ['.']:
        current_folder = Path(args.input[0]).name
    else:
        current_folder = Path(".").resolve().name
    tmdb_id, series_name = None, None

    if args.q:
        tmdb_id = args.q if args.q.isdigit() else None
        series_name = args.q if not tmdb_id else None
    else:
        tmdb_id, series_name = extract_from_folder_name(current_folder)

    if not tmdb_id and not series_name:
        print("Error: Could not determine TMDb ID or series name.")
        sys.exit(1)

    try:
        series_details = fetch_series_details(tmdb_id or series_name, API_KEY, args.lang)
        tmdb_id = series_details["id"]
        series_name = sanitize_filename(series_details["name"])
        print(f"Series found: {green_bold}{series_name} [tmdbid-{tmdb_id}]{reset}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Fetch season episode details (series details already fetched above)
    seasons = series_details.get("seasons", [])
    season_data_cache = {}
    season_numbers = {season["season_number"] for season in seasons}

    if args.season is not None and args.season not in season_numbers:
        season_numbers.add(args.season)

    for season_number in season_numbers:
        if args.season is not None and season_number != args.season:
            continue
        season_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}"
        try:
            season_response = requests.get(
                season_url,
                params={"api_key": API_KEY, "include_adult": "true", "language": args.lang},
                timeout=30,
            )
        except requests.RequestException as e:
            print(f"{red_bold}=Failed= to fetch Season {season_number} details: {e}{reset}")
            continue
        if season_response.status_code == 200:
            season_data_cache[season_number] = season_response.json()
            print(f"Fetched data for season {season_number}")
        else:
            print(f"{red_bold}=Failed= to fetch Season {season_number} details: {season_response.status_code}{reset}")
            continue

    # ============================================================
    # PHASE 1: Build rename mapping (source -> target)
    # ============================================================
    rename_mapping = {}
    unmatched_files = []

    for file in files:
        if not file.is_file() or "BitComet" in file.name or file.name == ".config":
            continue
        matched, final_output_path = process_file(file, series_name, season_data_cache, episode_shift, args, output_path)
        if matched:
            if final_output_path in rename_mapping.values():
                unmatched_files.append(file)
            else:
                rename_mapping[file] = final_output_path
        else:
            unmatched_files.append(file)

    # ============================================================
    # PHASE 1b: Detect conflicts and partition by action type
    # ============================================================
    source_paths = set(rename_mapping.keys())
    target_paths = set(rename_mapping.values())
    conflicting_targets = target_paths & source_paths

    executed = []
    errors = []
    skipped = []

    if args.action == "rename":
        non_conflicting = {}
        conflicting = {}
        for source, target in rename_mapping.items():
            if target in source_paths and target != source:
                conflicting[source] = target
            else:
                non_conflicting[source] = target

        for source, target in non_conflicting.items():
            result = _perform_rename(source, target, args, _perform_action)
            executed.append(source)
            if result == "error":
                errors.append(source)
            elif result == "skip":
                skipped.append(source)

        for source, target in conflicting.items():
            source_file_name, destin_file_name = _get_destin_display(source, target, args.output)
            print(f"{yellow}[SKIPPED]{reset} {source_file_name} {yellow}->{reset} {destin_file_name} {yellow}(Target collides with another source file){reset}")
            skipped.append(source)
    else:
        for source, target in rename_mapping.items():
            result = _perform_rename(source, target, args, _perform_action)
            executed.append(source)
            if result == "error":
                errors.append(source)
            elif result == "skip":
                skipped.append(source)

    # ============================================================
    # Summary
    # ============================================================
    total_processed = len(executed) + len(errors) + len(skipped)
    total_matched = total_processed + len(unmatched_files)

    if total_matched > 0 or args.action == "dry-run":
        if args.action == "dry-run":
            print(f"{green_bold}Total file(s) going to process: {total_matched}{reset}")
        else:
            print(f"{green_bold}Total file(s) processed: {total_matched}{reset}")

    if errors:
        print(f"{red_bold}{len(errors)} file(s) had errors{reset}")
        for err in errors:
            print(f"  {red}✗{reset} {err.name}")

    if unmatched_files:
        print(f"{yellow_bold}{len(unmatched_files)} file(s) skipped (no pattern match){reset}")
        for uf in unmatched_files[:10]:
            print(f"  {yellow}–{reset} {uf.name}")
        if len(unmatched_files) > 10:
            print(f"  {yellow}... and {len(unmatched_files) - 10} more{reset}")

    if not executed and not errors and not unmatched_files:
        print(f"{yellow_bold}No matching files found for processing.{reset}")


if __name__ == "__main__":
    main()
