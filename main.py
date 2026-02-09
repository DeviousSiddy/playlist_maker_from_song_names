import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import httpx
import os
from dotenv import load_dotenv

# This loads the variables from .env into the system environment
load_dotenv()

# Access them using os.getenv
client_id = os.getenv("YOUTUBE_CLIENT_ID")
client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

# Monkeypatch httpx.post to fix compatibility with youtube-search-python
_original_post = httpx.post
def _patched_post(*args, **kwargs):
    kwargs.pop("proxies", None)
    return _original_post(*args, **kwargs)
httpx.post = _patched_post

from youtubesearchpython import VideosSearch
from fuzzywuzzy import fuzz
import os

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.mp3 import MP3
except ImportError:
    EasyID3 = None

def get_song_metadata(song_list, use_gui=False):
    all_results = []
    
    for song_data in song_list:
        # Handle both dictionary (from folder scan) and string (legacy/manual)
        if isinstance(song_data, dict):
            query = song_data.get('query')
            display_name = song_data.get('display')
        else:
            query = song_data
            display_name = song_data

        print(f"Searching for: {display_name}...")
        
        def perform_search(query, target_name):
            search = VideosSearch(query, limit=5)
            result = search.result()
            results_list = result.get('result', [])
            best_match = None
            highest_score = 0
            
            if results_list:
                for video in results_list:
                    score = fuzz.token_sort_ratio(target_name, video['title'])
                    if score > highest_score:
                        highest_score = score
                        best_match = video
            return results_list, best_match, highest_score

        # Attempt 1: Search with "official" to prioritize official videos
        results_list, best_match, highest_score = perform_search(f"{query} official", query)
        
        selected_video = None
        
        if highest_score >= 80:
            selected_video = best_match
        else:
            print(f"  Score with 'official' too low ({highest_score}%). Retrying without...")
            # Attempt 2: Search without "official" (original query)
            results_list_2, best_match_2, highest_score_2 = perform_search(query, query)
            
            if highest_score_2 >= 80:
                selected_video = best_match_2
            else:
                # Fallback to user selection using results from the second (broader) search
                final_results = results_list_2 if results_list_2 else results_list
                final_score = highest_score_2 if results_list_2 else highest_score
                
                if final_results:
                    if use_gui:
                        prompt_text = f"Best match score ({final_score}) is low for '{display_name}'. Please choose:\n"
                        for i, video in enumerate(final_results):
                            prompt_text += f"{i + 1}. {video['title']} ({video['channel']['name']})\n"
                        prompt_text += "\nEnter number to select (or anything else to skip):"
                        choice_str = simpledialog.askstring("Select Video", prompt_text)
                        if choice_str and choice_str.isdigit():
                            choice = int(choice_str)
                            if 1 <= choice <= len(final_results):
                                selected_video = final_results[choice - 1]
                    else:
                        print(f"  Best match score ({final_score}) is low. Please choose:")
                        for i, video in enumerate(final_results):
                            print(f"    {i + 1}. {video['title']} ({video['channel']['name']})")
                        
                        choice = input("  Enter 1-5 to select (or anything else to skip): ")
                        if choice.isdigit() and 1 <= int(choice) <= len(final_results):
                            selected_video = final_results[int(choice) - 1]
                else:
                    print(f"No results found for {display_name}")

        if selected_video:
            # Extracting exactly what you asked for
            metadata = {
                "search_query": query,
                "video_name": selected_video['title'],
                "channel_name": selected_video['channel']['name'],
                "url": selected_video['link']
            }
            all_results.append(metadata)

    return all_results

def get_songs_from_folder(folder_path):
    songs = []
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return []

    print(f"Scanning folder: {folder_path}")
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.mp3', '.flac', '.m4a', '.wav')):
            file_path = os.path.join(folder_path, filename)
            # Default to filename without extension
            base_name = os.path.splitext(filename)[0]
            song_info = {'query': base_name, 'display': base_name}
            
            # Try to read MP3 metadata if mutagen is available
            if EasyID3 and filename.lower().endswith('.mp3'):
                try:
                    audio = MP3(file_path, ID3=EasyID3)
                    title = audio.get('title', [None])[0]
                    artist = audio.get('artist', [None])[0]
                    if title and artist:
                        song_info['query'] = f"{title} {artist}"
                        song_info['display'] = f"{title} - {artist}"
                    elif title:
                        song_info['query'] = title
                        song_info['display'] = title
                except Exception:
                    pass # Fallback to filename on error
            
            songs.append(song_info)
            print(f"  Found: {song_info['display']}")
    return songs

def add_to_youtube(video_ids):
    if not GOOGLE_API_AVAILABLE:
        messagebox.showerror("Error", "Google API libraries not installed.\nPlease run: pip install -r requirement.txt")
        return

    scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]
    flow = None

    # 1. Try keys/client_secret.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "keys", "client_secret.json")

    if os.path.exists(json_path):
        try:
            flow = InstalledAppFlow.from_client_secrets_file(json_path, scopes)
        except Exception as e:
            print(f"Failed to load from {json_path}: {e}")

    # 2. Try Environment Variables
    if not flow and client_id and client_secret:
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"]
            }
        }
        try:
            flow = InstalledAppFlow.from_client_config(client_config, scopes)
        except Exception as e:
            print(f"Failed to load from environment variables: {e}")

    # 3. Fallback to File Dialog
    if not flow:
        messagebox.showinfo("Authentication", "To add a playlist to your account, you need a 'client_secret.json' file.\n\nIt was not found in the 'keys' folder, and environment variables are missing.\n\nPlease select it manually.")
        client_secrets_file = filedialog.askopenfilename(
            title="Select client_secret.json", 
            filetypes=[("JSON Files", "*.json")]
        )
        if not client_secrets_file:
            return
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
    
    try:
        # Perform OAuth flow
        creds = flow.run_local_server(port=0)
        youtube = build("youtube", "v3", credentials=creds)
        
        # Create Playlist
        playlist_response = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": "My Generated Playlist",
                    "description": "Created with Playlist Maker from Song Names",
                },
                "status": {"privacyStatus": "private"}
            }
        ).execute()
        
        playlist_id = playlist_response["id"]
        
        # Add Videos
        for vid in video_ids:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": vid}
                    }
                }
            ).execute()
            
        messagebox.showinfo("Success", "Playlist created successfully on your account!")
        
    except Exception as e:
        messagebox.showerror("API Error", f"An error occurred:\n{e}")

def create_ui():
    root = tk.Tk()
    root.title("Playlist Maker")
    root.geometry("400x150")

    lbl_instruction = tk.Label(root, text="Select a folder with music files to generate a YouTube playlist.")
    lbl_instruction.pack(pady=10)

    def on_select_folder():
        folder_path = filedialog.askdirectory()
        if folder_path:
            my_songs = get_songs_from_folder(folder_path)
            if not my_songs:
                messagebox.showinfo("Info", "No songs found in the selected folder.")
                return
            
            data = get_song_metadata(my_songs, use_gui=True)
            
            video_ids = [item['url'].split("v=")[-1] for item in data]
            if video_ids:
                playlist_url = "https://www.youtube.com/watch_videos?video_ids=" + ",".join(video_ids)
                root.clipboard_clear()
                root.clipboard_append(playlist_url)
                root.update()
                
                # Custom Success Window
                success_win = tk.Toplevel(root)
                success_win.title("Success")
                success_win.geometry("450x200")
                
                tk.Label(success_win, text="Playlist generated and URL copied to clipboard!", fg="green", font=("Arial", 10, "bold")).pack(pady=10)
                
                entry = tk.Entry(success_win, width=60)
                entry.insert(0, playlist_url)
                entry.configure(state="readonly")
                entry.pack(pady=5)
                
                tk.Button(success_win, text="Add to My YouTube Account (OAuth)", command=lambda: add_to_youtube(video_ids), bg="#cc0000", fg="white").pack(pady=15)
                tk.Button(success_win, text="Close", command=success_win.destroy).pack(pady=5)
            else:
                messagebox.showwarning("Warning", "No videos found.")

    btn_select = tk.Button(root, text="Select Folder", command=on_select_folder, height=2, width=20)
    btn_select.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    create_ui()