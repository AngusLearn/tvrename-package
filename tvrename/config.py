# tvrename/config.py
import configparser
from pathlib import Path

def load_config(config_path):
    """Loads the configuration from the specified path."""
    episode_shift = 0
    if config_path.exists() and not config_path.is_dir():
        print("Configuration file found. Loading values...")
        config = configparser.ConfigParser()
        config.read(config_path)
        episode_shift = int(config["ShiftConfig"].get("episode_shift", 0))
        print(f"Episode shift is set to {episode_shift}")
    else:
        if config_path.is_dir():
            print(".config is a directory, skipping configuration load.")
        else:
            print("No configuration file found. Proceeding without shift.")
    return episode_shift
