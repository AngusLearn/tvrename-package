# tvrename

A command-line tool to rename and organize TV series files automatically using data from The Movie Database (TMDb).

## Description

`tvrename` is a command-line tool designed to simplify the process of renaming and organizing your TV series files. It fetches episode information from The Movie Database (TMDb) and uses that data to rename your files according to a consistent and customizable format. This makes it easier to manage your media library and keep your files organized.

## Features

*   **Automatic Renaming:**  Renames TV series files based on data from TMDb.
*   **Customizable Formats:**  Supports custom naming formats using placeholders for series name, season number, episode number, episode title, etc.
*   **Wildcard Input:** Accepts wildcard patterns to process multiple files at once (e.g., `*mkv`, `*.ass`).
*   **TMDb ID or Series Title:**  Can identify series using either the TMDb ID or the series title.
*   **Dry-Run Mode:**  Allows you to preview the changes before actually renaming files.
*   **Copy or Rename:**  Supports both renaming and copying files to a new location.
*   **Episode Shift:**  Handles cases where local episode numbering differs from TMDb (e.g. using a `.config` file with an `episode_shift` setting).
*   **Configuration File:**  Supports a `.config` file for specifying an episode shift.
*   **Colorized Output:** Provides informative and visually appealing output using `colorama`.

## Installation

    You can install `tvrename` directly from the GitHub repository using `pip`:

    ```
    pip install git+https://github.com/AngusLearn/tvrename-package.git
    ```
    
    or


1.  **Clone the repository:**

    ```
    git clone https://github.com/AngusLearn/tvrename-package.git
    cd tvrename-package
    ```


2.  **Create a virtual environment (recommended):**

    ```
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate  # On Windows
    ```

3.  **Install the package and dependencies:**

    ```
    pip install -e .
    ```

4.  **Register an account and obtain a TMDb API Key:**

    *   This script requires an API key from [The Movie Database (TMDb)](https://www.themoviedb.org/).
    *   **Why?** The API key allows the script to fetch series and episode information automatically.
    *   **How to get an API key:**
        1.  Go to [https://www.themoviedb.org/](https://www.themoviedb.org/) and click "Join TMDb" to create a free account.
        2.  After creating your account, log in and navigate to your account settings (usually by clicking your profile picture).
        3.  Look for a section called "API" or "Request an API Key".
        4.  Fill out the required information to request an API key.  You may need to provide a brief description of how you plan to use the API.
        5.  Once your request is approved, you will receive your API key.
    *   **Keep your API key safe!**  Treat it like a password and don't share it publicly.


5.  **Set the API Key as an Environment Variable:**

    You need to set the TMDb API key as an environment variable named `API_KEY`. The script looks for this variable in a `.env` file located at `/etc/tvrename/.env`.  Create this file (if it doesn't exist) and add the following line:

    ```
    API_KEY=YOUR_TMDB_API_KEY
    ```

    (Replace `YOUR_TMDB_API_KEY` with your actual API key.)

## Usage

tvrename [options]

**Options:**

*   `--q SERIES_TITLE_OR_TMDB_ID`, `--q SERIES_TITLE_OR_TMDB_ID`: TMDb ID or series title to search for.
*   `--input INPUT`: Path to the input directory or file (supports wildcards). Accepts multiple patterns (e.g. `"*mkv" "*.ass"`). Defaults to the current directory.
*   `--format FORMAT`: Custom format for renaming files.  Supports placeholders like `{n}` (series name), `{t}` (episode title), and `{s00e00}` (season and episode number).  Also supports `.take(length)` for truncation.
*   `--lang LANG`: Language for TMDb data (default: `ja-JP`).
*   `--season SEASON`: Process only a specific season (default: all).
*   `--output OUTPUT`: Output directory for renamed files.
*   `--action {dry-run,rename,copy}`: Action to perform (default: `dry-run`).
*   `--help`: Show this help message and exit.

**Examples:**

*   **Dry-run rename of all `.mkv` files in the current directory, searching for "My Series" on TMDb:**

    ```
    tvrename --input "*.mkv" --q "My Series" --action dry-run
    ```

*   **Rename all `.mkv` and `.ass` files in the "episodes" directory, using TMDb ID 12345, and copy them to the "/output" directory:**

    ```
    tvrename --input "episodes/*mkv" "episodes/*.ass" --q 12345 --output "/output" --action copy
    ```

*   **Rename files in the current directory using a custom format:**

    ```
    tvrename --q "My Series" --format "{n} - {s00e00} - {t.take(30)}" --action rename
    ```

    (This example truncates the episode title to 30 characters.)

*   **Rename files in the current directory, automatically determining the series based on the folder name (e.g. "Series Name [tmdbid-12345]"):**

    ```
    tvrename --action rename
    ```

## Configuration File

You can use a `.config` file in the input directory to specify an episode shift. This is useful if your local episode numbering is different from TMDb. The `.config` file should have the following format:

.config
```
[ShiftConfig]
episode_shift = 1
```


This example sets the episode shift to 1, meaning that the script will subtract 1 from the TMDb episode number to determine the local episode number.

## Contributing

Contributions are welcome! If you'd like to contribute to `tvrename`, please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes.
4.  Test your changes thoroughly.
5.  Submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).  See the `LICENSE` file for details.



