# Playlist Maker from Song Names

A Python tool that scans a local folder of music files, searches for them on YouTube, and automatically generates a YouTube playlist URL containing those songs.

## Features

- **Folder Scanning**: Recursively scans a selected directory for audio files (`.mp3`, `.flac`, `.m4a`, `.wav`).
- **Smart Metadata Extraction**: 
  - Reads ID3 tags (Artist & Title) from MP3 files for accurate searching.
  - Falls back to filenames if metadata is missing.
- **Fuzzy Matching**: Uses `fuzzywuzzy` to compare search results with your song names.
  - Automatically selects high-confidence matches (>80%).
  - Prompts you to manually select the correct video for low-confidence matches.
- **Simple GUI**: Built with `tkinter` for easy folder selection.
- **Clipboard Integration**: Automatically copies the final playlist link to your clipboard.
- **YouTube Account Integration**: Authenticate with your Google account to create the playlist directly on YouTube.

## Prerequisites

- Python 3.x

## Installation

1. Clone or download this repository.
2. Install the required dependencies using `pip`:

```bash
pip install -r requirement.txt
```

*Note: The `requirement.txt` should include:*
- `youtube-search-python`
- `mutagen`
- `fuzzywuzzy`
- `python-Levenshtein`
- `google-auth-oauthlib`
- `google-api-python-client`
- `python-dotenv`

## Google API Setup (Optional)

To use the "Add to My YouTube Account" feature, you need OAuth 2.0 credentials from the Google Cloud Console.

1. Create a project and enable the **YouTube Data API v3**.
2. Create **OAuth 2.0 Client IDs** (Desktop App).
3. Download the JSON file.
4. **Option A (Recommended)**: Rename it to `client_secret.json` and place it in a folder named `keys` inside the project directory.
5. **Option B**: Create a `.env` file in the project root with:
   ```
   YOUTUBE_CLIENT_ID=your_client_id
   YOUTUBE_CLIENT_SECRET=your_client_secret
   ```

## Usage

1. Run the script:
   ```bash
   python main.py
   ```
2. A small window will appear. Click **Select Folder**.
3. Choose the directory containing your music files.
4. The script will search for each song. If a match is ambiguous, a popup will ask you to choose the correct video.
5. Once finished, a success window will appear.
6. You can copy the generated link or click **Add to My YouTube Account** to save it directly to your channel.