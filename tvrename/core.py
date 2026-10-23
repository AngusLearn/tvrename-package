# tvrename/core.py
import os
import shutil
import requests
import re
from pathlib import Path
from .utils import sanitize_filename, apply_truncation, get_full_extension, normalize_filename, yellow, green, yellow_bold, red_bold, green_bold, light_blue, reset


def _match_quality(normalized, match_obj, matched_name, episode_num):
    """Score match quality. Higher = more specific/precise."""
    text = match_obj.group()
    if not text:
        return 40

    if re.search(r'S\d{2}E\d{2}', text, re.IGNORECASE):
        return 100
    if text.lstrip().startswith('-'):
        return 90
    if text.lstrip()[0] in '([':
        return 80
    if re.match(r'[Ee]p', text):
        return 75
    if 'Vol' in text:
        return 70
    if text.lstrip().startswith('#'):
        return 65
    if re.search(r'\d{2}', text):
        return 60
    return 50


def fetch_series_details(query, api_key, lang="ja-JP"):
    """Fetches series details from TMDb."""
    params = {"api_key": api_key, "include_adult": "true", "language": lang}
    if query.isdigit():
        url = f"https://api.themoviedb.org/3/tv/{query}"
    else:
        url = "https://api.themoviedb.org/3/search/tv"
        params["query"] = query
    response = requests.get(url, params=params, timeout=30)
    if response.status_code == 200:
        data = response.json()
        if query.isdigit():  # If searching by ID
            if not data.get("id"):  # Check if 'id' exists in the response
                raise Exception(f"No series found with ID: {query}")
            return data
        else:
            if "results" in data and data["results"]:
                return data["results"][0]
            else: # Raise an Exception if no results are found
                raise Exception(f" =Failure= No series found matching query: {query}")
    else:
        raise Exception(f" =Failure= to fetch data from TMDb: {response.status_code} - {response.text}")


def _clean_old_hardlinks(output_path, source_file, new_hardlink_path):
    """Remove old hardlinks in destination dir with same inode as source."""
    dest_dir = Path(output_path) if output_path else None
    if not dest_dir or not dest_dir.exists():
        return

    source_inode = source_file.stat().st_ino

    for f in dest_dir.rglob("*"):
        if f.is_file() and f.resolve() != new_hardlink_path.resolve():
            try:
                if f.stat().st_ino == source_inode:
                    f.unlink()
            except OSError:
                pass


def _perform_action(file, final_output_path, source_file_name, destin_file_name, args):
    """Performs the rename/copy/hardlink action with error handling."""
    final_output_path.parent.mkdir(parents=True, exist_ok=True)

    if final_output_path.exists() and not (args.action == "hardlink" and args.rename_hardlink):
        if args.action == "dry-run":
            print(f"{yellow}[DRY-RUN]{reset} {red_bold}[SKIPPING]{reset} {source_file_name} {yellow}->{reset} {destin_file_name} {red_bold}(Target file already exists){reset}")
        else:
            print(f"{red_bold}[SKIPPING]{reset} {source_file_name} {red_bold}->{reset} {destin_file_name} {red_bold}(Target file already exists){reset}")
        return "skip"

    if args.action == "dry-run":
        print(f"{yellow_bold}[DRY-RUN]{reset} {green}[RENAME]{reset} {source_file_name} {yellow_bold}->{reset} {destin_file_name}")
    elif args.action == "rename":
        try:
            file.rename(final_output_path)
            print(f"{green_bold}[RENAMED]{reset} {source_file_name} {green_bold}->{reset} {destin_file_name}")
            return "success"
        except OSError as e:
            if e.errno == 18:  # cross-device link
                print(f"{yellow}[INFO]{reset} Cross-device move detected, using fallback for {source_file_name}")
                try:
                    shutil.move(str(file), str(final_output_path))
                    print(f"{green_bold}[MOVED]{reset} {source_file_name} {green_bold}->{reset} {destin_file_name}")
                    return "success"
                except OSError as e2:
                    print(f"{red_bold}[ERROR]{reset} Failed to move {source_file_name}: {e2}")
                    return "error"
            else:
                print(f"{red_bold}[ERROR]{reset} Failed to rename {source_file_name}: {e}")
                return "error"
    elif args.action == "copy":
        try:
            final_output_path.write_bytes(file.read_bytes())
            print(f"{green_bold}[COPIED]{reset} {source_file_name} {green_bold}->{reset} {destin_file_name}")
            return "success"
        except OSError as e:
            print(f"{red_bold}[ERROR]{reset} Failed to copy {source_file_name}: {e}")
            return "error"
    elif args.action == "hardlink":
        # Hardlink in the same directory is not a valid action — there's no
        # way to distinguish "origin" from "hardlinks" once the folder is
        # populated, and episode name changes on TMDB would create yet
        # another hardlink with no way to know which is the original.
        if file.parent == final_output_path.parent:
            print(f"{yellow}[SKIPPED]{reset} Hardlink in the same directory is not supported: {source_file_name}")
            return "skip"

        try:
            if final_output_path.exists():
                if os.stat(file).st_ino == os.stat(final_output_path).st_ino:
                    if args.rename_hardlink:
                        _clean_old_hardlinks(args.output, file, final_output_path)
                    print(f"{yellow}[SKIPPED]{reset} Hardlink already exists: {final_output_path}")
                    return "skip"
                else:
                    final_output_path.unlink()
                    os.link(file, final_output_path)
                    print(f"{green_bold}[RENAMED HARDLINK]{reset} {source_file_name} {green_bold}->{reset} {destin_file_name}")
                    if args.rename_hardlink:
                        _clean_old_hardlinks(args.output, file, final_output_path)
                    return "success"
            else:
                os.link(file, final_output_path)
                print(f"{light_blue}[HARDLINKED]{reset} {source_file_name} {light_blue}->{reset} {destin_file_name}")
                if args.rename_hardlink:
                    _clean_old_hardlinks(args.output, file, final_output_path)
                return "success"
        except OSError as e:
            print(f"{red_bold}[ERROR]{reset} Failed to create hardlink for {source_file_name}: {e}")
            return "error"
    return "success"


def process_file(file, series_name, season_data_cache, episode_shift, args, output_path):
    """Processes a single file, attempting to rename it based on TMDb data.

    Uses two-phase matching: first collects ALL possible matches across all
    episodes, then picks the best one by match quality score.
    """
    normalized = normalize_filename(file.name)

    # PHASE 1: Collect all possible matches with their quality scores
    all_matches = []

    for season_number, season_data in season_data_cache.items():
        episodes = season_data.get("episodes", [])
        if not episodes:
            continue

        for episode in episodes:
            tmdb_episode_number = episode["episode_number"]
            local_episode_number = tmdb_episode_number - episode_shift

            if local_episode_number < 0:
                continue

            episode_title = sanitize_filename(episode["name"])

            if not args.format:
                new_name = f"{series_name} - S{season_number:02d}E{tmdb_episode_number:02d} - {episode_title}"
            else:
                new_name = args.format
                new_name = apply_truncation(new_name, "n", series_name)
                new_name = apply_truncation(new_name, "t", episode_title)
                new_name = new_name.replace("{s00e00}", f"S{season_number:02d}E{tmdb_episode_number:02d}")

            multi_episode_patterns = [
                rf"\bS{season_number:02d}E{local_episode_number:02d}-(\d{{2,3}})\b",
                rf"\b{local_episode_number:02d}-(\d{{2,3}})\b",
            ]

            multi_episode_match = None
            for pattern in multi_episode_patterns:
                multi_episode_match = re.search(pattern, normalized, re.IGNORECASE)
                if multi_episode_match:
                    break

            if multi_episode_match:
                range_end = int(multi_episode_match.group(1))
                if range_end >= local_episode_number:
                    episode_titles = [
                        sanitize_filename(ep["name"])
                        for ep in episodes
                        if tmdb_episode_number <= ep["episode_number"] <= range_end
                    ]
                    if episode_titles:
                        range_str = f"S{season_number:02d}E{local_episode_number:02d}-{range_end:02d}"
                        title_str = " ／ ".join(episode_titles)
                        if not args.format:
                            new_name = f"{series_name} - {range_str} - {title_str}"
                        else:
                            new_name = args.format
                            new_name = apply_truncation(new_name, "n", series_name)
                            new_name = apply_truncation(new_name, "t", title_str)
                            new_name = new_name.replace("{s00e00}", range_str)

            patterns = [
                rf"\bS{season_number:02d}E{local_episode_number:02d}\b",
                rf"\bS{season_number:02d}EP{local_episode_number:02d}\b",
                rf"\b0?{season_number}x{local_episode_number:02d}\b",
                rf"\b{season_number}xSpecial {local_episode_number}\b",
                rf"(-| |\[|.)S{season_number:02d}E{local_episode_number:02d}(?:v\d{{1}})?(\]| |-|\[|\.)",
            ]

            next_patterns = [
                rf"^0?{local_episode_number}(\.| )",
                rf"(-| |\[|\()0?{local_episode_number}(\]| |-|\[|\.|\))",
                rf"(-| |\[){local_episode_number:03d}(\]| |-|\[|\.)",
                rf"_0?{local_episode_number}_",
                rf"(-| |\[|_){local_episode_number:02d}v\d{{1}}(\(|\]| |-|\[|\.|_)",
                rf"第0?{local_episode_number}[弾話章话巻怪幕節夜回]",
                rf" EP0?{local_episode_number} ",
                rf"( |_)Ep0?{local_episode_number}(_| |\.)",
                rf" E0?{local_episode_number} ",
                rf"\.EP{local_episode_number:02d}\.",
                rf"Vol\.0?{local_episode_number}",
                rf"Epilogue.0?{local_episode_number}",
                rf"＃0?{local_episode_number}",
                rf"Episode 0?{local_episode_number}",
                rf" #0?{local_episode_number}",
                rf"(-| |\[|)#({local_episode_number}|{local_episode_number:02d}) ",
                rf"SP{local_episode_number:02d}",
                rf"\[{local_episode_number:02d} ?(END|FIN)\]",
                rf"\[{local_episode_number:02d}_?(END|FIN)\]",
                rf"Part\.0?{local_episode_number}",
            ]

            # Collect matches for this episode
            for pattern in patterns + next_patterns:
                m = re.search(pattern, normalized, re.IGNORECASE)
                if m:
                    score = _match_quality(normalized, m, new_name, local_episode_number)
                    new_file_name = f"{new_name}{get_full_extension(file.name)}"
                    dest_dir = Path(output_path) if output_path else file.parent
                    final_output_path = dest_dir / new_file_name
                    all_matches.append((score, season_number, tmdb_episode_number, local_episode_number, new_name, final_output_path))
                    break

    # PHASE 2: Pick the best match by quality score
    if all_matches:
        all_matches.sort(key=lambda x: x[0], reverse=True)
        best_score, _, _, _, _, best_path = all_matches[0]
        return True, best_path

    return False, None
