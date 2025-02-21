#!/usr/bin/env python3
# tvrename/main.py
import os
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style
from glob import glob

from .args import parse_arguments
from .config import load_config
from .core import fetch_series_details, process_file
from .utils import sanitize_filename, extract_from_folder_name #Import extract from folder name function
import requests  # Import requests here


# Regular colors
yellow = "\033[33m"
red = "\033[31m"
green = "\033[32m"

# Bold colors
yellow_bold = "\033[1;33m"
red_bold = "\033[1;31m"
green_bold = "\033[1;32m"

# Reset
reset = "\033[0m"

# Initialize colorama
init(autoreset=True)

# Load environment variables from .env file
dotenv_path = os.getenv("DOTENV_PATH", "/etc/tvrename/.env")
load_dotenv(dotenv_path=dotenv_path)

# Accessing the API key
API_KEY = os.getenv("API_KEY")

def main():
    """Main function to run the tvrename script."""
    args = parse_arguments()

    # Collect files from all input patterns
    files = []
    for input_pattern in args.input:
        # Resolve input path
        input_path_str = input_pattern
        input_path = Path(input_path_str).resolve()

        if '*' in input_path_str:
            # Find the directory containing the wildcard
            base_dir = Path(os.path.dirname(input_path_str)).resolve()
            if not base_dir.exists():
                print(f"Error: The specified input path does not exist: {base_dir}")
                continue  # Skip to the next pattern

            # Use glob to find files matching the wildcard
            found_files = [Path(f).resolve() for f in glob(input_path_str)]
            if not found_files:
                print(f"Warning: No files found matching the wildcard: {input_path_str}")  # Changed to warning
                continue  # Skip to the next pattern
            files.extend(found_files)
        else:
            if not input_path.exists():
                print(f"Error: The specified input path does not exist: {input_path}")
                continue  # Skip to the next pattern
            if input_path.is_file():
                files.append(input_path)
            else:  # is directory
                if args.recursive: # Added recursive check
                    files.extend([f for f in input_path.rglob("*") if f.is_file()]) # ADDED: rglob
                else:
                    files.extend([f for f in input_path.iterdir() if f.is_file()])

    if not files:
        print("Error: No files found based on the provided input patterns.")
        exit(1)

    # Resolve output path
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
    if args.input and args.input != ['.']: #If input is not default value
        current_folder = Path(args.input[0]).name
    else:
        current_folder = Path(".").resolve().name  # Get the real current directory
    tmdb_id, series_name = None, None

    if args.q:
        tmdb_id = args.q if args.q.isdigit() else None
        series_name = args.q if not tmdb_id else None
    else:
        tmdb_id, series_name = extract_from_folder_name(current_folder)

    if not tmdb_id and not series_name:
        print("Error: Could not determine TMDb ID or series name.")
        exit(1)

    try:
        series_details = fetch_series_details(tmdb_id or series_name, API_KEY, args.lang)
        tmdb_id = series_details["id"]
        series_name = sanitize_filename(series_details["name"])
        print(f"Series found: {green_bold}{series_name} [tmdbid-{tmdb_id}]{reset}")
    except Exception as e:
        print(f"Error: {e}") #Modified
        exit(1)

    # Fetch season and episode details
    details_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={API_KEY}&include_adult=true&language={args.lang}"
    response = requests.get(details_url)
    if response.status_code != 200:
        print(f"Failed to fetch series details: {response.status_code}")
        exit(1)

    details_data = response.json()
    seasons = details_data.get("seasons", [])

    # Fetch and cache season data
    season_data_cache = {}
    season_numbers = {season["season_number"] for season in seasons}

    # Add the specified season if it is not in the list
    if args.season is not None and args.season not in season_numbers:
        season_numbers.add(args.season)

    for season_number in season_numbers:
        if args.season is not None and season_number != args.season:
            # print(f"Skipping season {season_number} as it does not match the specified season {args.season}")
            continue

        season_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}?api_key={API_KEY}&include_adult=true&language={args.lang}"
        season_response = requests.get(season_url)
        if season_response.status_code == 200:
            season_data_cache[season_number] = season_response.json()
            print(f"Fetched data for season {season_number}")
        else:
            print(f"{red_bold}=Failed= to fetch Season {season_number} details: {season_response.status_code}{reset}")
            continue

    # Initialize processed files counter and a flag to check if any file was processed
    processed_files_count = 0
    any_file_processed = False

    # Process files using cached data
    for file in files:
        # print(f"Processing file: {file.name}")
        if not file.is_file() or "BitComet" in file.name:
            continue

        #process_file(file, series_name, season_data_cache, episode_shift, args, output_path)
        if process_file(file, series_name, season_data_cache, episode_shift, args, output_path):
            processed_files_count += 1
            any_file_processed = True  # Set the flag to True if any file was processed
            
    # Print the total number of processed files
    if any_file_processed:
        if args.action == "dry-run":
            print(f"{green_bold}Total file(s) going to processe: {processed_files_count}{reset}")
        else:
            print(f"{green_bold}Total file(s) processed: {processed_files_count}{reset}")
    else:
        print(f"{yellow_bold}No matching files found for processing.{reset}")

# Add this block
if __name__ == "__main__":
    main()
