# tvrename/core.py
import requests
import re
from pathlib import Path
from .utils import sanitize_filename, apply_truncation  # Relative import
from colorama import init, Fore, Style

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


def fetch_series_details(query, api_key, lang="ja-JP"):
    """Fetches series details from TMDb."""
    if query.isdigit():
        url = f"https://api.themoviedb.org/3/tv/{query}?api_key={api_key}&include_adult=true&language={lang}"
    else:
        url = f"https://api.themoviedb.org/3/search/tv?query={query}&api_key={api_key}&include_adult=true&language={lang}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "results" in data and data["results"]:
            return data["results"][0]
        return data
    else:
        raise Exception(f"Failed to fetch data from TMDb: {response.status_code} - {response.text}")


def process_file(file, series_name, season_data_cache, episode_shift, args, output_path):
    """Processes a single file, attempting to rename it based on TMDb data."""
    file_processed = False
    for season_number, season_data in season_data_cache.items():
        episodes = season_data.get("episodes", [])
        for episode in episodes:
            tmdb_episode_number = episode["episode_number"]
            local_episode_number = tmdb_episode_number - episode_shift

            if local_episode_number <= 0:
                continue

            episode_title = sanitize_filename(episode["name"])

            if not args.format:
                new_name = f"{series_name} - S{season_number:02d}E{tmdb_episode_number:02d} - {episode_title}"
            else:
                new_name = args.format
                new_name = apply_truncation(new_name, "n", series_name)
                new_name = apply_truncation(new_name, "t", episode_title)
                new_name = new_name.replace("{s00e00}", f"S{season_number:02d}E{tmdb_episode_number:02d}")

            patterns = [
                rf"\bS{season_number:02d}E{local_episode_number:02d}\b",
                rf"\b{season_number}x{local_episode_number:02d}\b",
                rf"\b{season_number}xSpecial {local_episode_number}\b",
            ]

            next_patterns = [
                rf"^{local_episode_number:02d}\.",
                rf"- {local_episode_number:02d} -",
                rf" -{local_episode_number:02d}-",
                rf"- {local_episode_number:02d} ",
                rf"- {local_episode_number:02d} \[",
                rf" {local_episode_number:02d}[.| ]",
                rf"_0?{local_episode_number}_",
                rf"\[{local_episode_number:02d}\]",
                rf"\[{local_episode_number:02d}v\d{{1}}\]",
                rf"第0?{local_episode_number}[話章话巻怪幕節夜]",
                rf" EP0?{local_episode_number} ",
                rf".EP{local_episode_number:02d}.",
                rf"Vol\.0?{local_episode_number}",
                rf"Epilogue.0?{local_episode_number}",
                rf"＃0?{local_episode_number}",
                rf"Episode 0?{local_episode_number}",
                rf" #0?{local_episode_number}",
                rf"SP{local_episode_number:02d}",
                rf"\[.*{local_episode_number:02d}\]",
                rf"ACT\.{local_episode_number}",
            ]

            for pattern in patterns:
                if re.search(pattern, file.name, re.IGNORECASE):
                    new_file_name = f"{new_name}{file.suffix}"
                    final_output_path = (output_path if output_path else file.parent) / new_file_name

                    output_parent = str(Path(final_output_path).parent)
                    file_parent = str(Path(file).parent)

                    if output_parent == file_parent:
                        destin_file_name = str(Path(final_output_path).relative_to(output_parent))
                        source_file_name = str(Path(file).relative_to(output_parent))
                    else:
                        destin_file_name = final_output_path
                        source_file_name = file

                    if final_output_path.exists():
                        if args.action == "dry-run":
                            print(f"{Fore.YELLOW}[DRY-RUN]{Style.RESET_ALL} {red_bold}[SKIPPING]{reset} {source_file_name} {Fore.YELLOW}->{Style.RESET_ALL} {destin_file_name} {red_bold}(Target file already exists){reset}")
                        else:
                            print(f"{red_bold}[SKIPPING]{reset} {source_file_name} {red_bold}->{reset} {destin_file_name} {red_bold}(Target file already exists){reset}")
                        break

                    if args.action == "dry-run":
                        print(f"{yellow_bold}[DRY-RUN]{reset} {Fore.GREEN}[RENAME]{Style.RESET_ALL} {source_file_name} {yellow_bold}->{reset} {destin_file_name}")
                    elif args.action == "rename":
                        final_output_path.parent.mkdir(parents=True, exist_ok=True)
                        file.rename(final_output_path)
                        print(f"{green_bold}[RENAMED]{reset} {source_file_name} {green_bold}->{reset} {destin_file_name}")
                    elif args.action == "copy":
                        final_output_path.parent.mkdir(parents=True, exist_ok=True)
                        final_output_path.write_bytes(file.read_bytes())
                        print(f"{green_bold}[COPIED]{reset} {source_file_name} {green_bold}->{reset} {destin_file_name}")
                    file_processed = True
                    break

            if file_processed:
                break

            if re.search(rf"S\d{{2}}E\d{{2,3}}", file.name, re.IGNORECASE) or \
                re.search(rf"\b\d{{2}}x\d{{2,3}}\b", file.name, re.IGNORECASE) or \
                re.search(rf"\d{{1,2}}xSpecial \d{{1,3}}", file.name, re.IGNORECASE):
                continue

            for next_pattern in next_patterns:
                if re.search(next_pattern, file.name, re.IGNORECASE):
                    new_file_name = f"{new_name}{file.suffix}"
                    final_output_path = (output_path if output_path else file.parent) / new_file_name

                    output_parent = str(Path(final_output_path).parent)
                    file_parent = str(Path(file).parent)

                    if output_parent == file_parent:
                        destin_file_name = str(Path(final_output_path).relative_to(output_parent))
                        source_file_name = str(Path(file).relative_to(output_parent))
                    else:
                        destin_file_name = final_output_path
                        source_file_name = file

                    if final_output_path.exists():
                        if args.action == "dry-run":
                            print(f"{Fore.YELLOW}[DRY-RUN]{Style.RESET_ALL} {red_bold}[SKIPPING]{reset} {source_file_name} {Fore.YELLOW}->{Style.RESET_ALL} {destin_file_name} {red_bold}(Target file already exists){reset}")
                        else:
                            print(f"{red_bold}[SKIPPING]{reset} {source_file_name} {red_bold}->{reset} {destin_file_name} {red_bold}(Target file already exists){reset}")
                        break

                    if args.action == "dry-run":
                        print(f"{yellow_bold}[DRY-RUN]{reset} {Fore.GREEN}[RENAME]{Style.RESET_ALL} {source_file_name} {yellow_bold}->{reset} {destin_file_name}")
                    elif args.action == "rename":
                        final_output_path.parent.mkdir(parents=True, exist_ok=True)
                        file.rename(final_output_path)
                        print(f"{green_bold}[RENAMED]{reset} {source_file_name} {green_bold}->{reset} {destin_file_name}")
                    elif args.action == "copy":
                        final_output_path.parent.mkdir(parents=True, exist_ok=True)
                        final_output_path.write_bytes(file.read_bytes())
                        print(f"{green_bold}[COPIED]{reset} {source_file_name} {green_bold}->{reset} {destin_file_name}")
                    file_processed = True
                    break

    return file_processed
