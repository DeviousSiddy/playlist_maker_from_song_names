import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import httpx

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
    from mutagen.easyid3 import EasyID3
    from mutagen.mp3 import MP3
except ImportError:
    EasyID3 = None

def get_song_metadata(song_list, use_gui=False):
    all_results = []
    
    for song in song_list:
        print(f"Searching for: {song}...")
        
        # limit=1 ensures we only get the top result (saves time/data)
        search = VideosSearch(song, limit=5)
        result = search.result()
        results_list = result.get('result', [])
        
        if not results_list:
            print(f"No results found for {song}")
            continue

        best_match = None
        highest_score = 0

        for video in results_list:
            score = fuzz.token_sort_ratio(song, video['title'])
            if score > highest_score:
                highest_score = score
                best_match = video

        selected_video = None
        if highest_score >= 80:
            selected_video = best_match
        else:
            if use_gui:
                prompt_text = f"Best match score ({highest_score}) is low for '{song}'. Please choose:\n"
                for i, video in enumerate(results_list):
                    prompt_text += f"{i + 1}. {video['title']} ({video['channel']['name']})\n"
                choice = simpledialog.askinteger("Select Video", prompt_text, minvalue=1, maxvalue=len(results_list))
                if choice:
                    selected_video = results_list[choice - 1]
            else:
                print(f"  Best match score ({highest_score}) is low. Please choose:")
                for i, video in enumerate(results_list):
                    print(f"    {i + 1}. {video['title']} ({video['channel']['name']})")
                
                choice = input("  Enter 1-5 to select (or anything else to skip): ")
                if choice.isdigit() and 1 <= int(choice) <= len(results_list):
                    selected_video = results_list[int(choice) - 1]

        if selected_video:
            # Extracting exactly what you asked for
            metadata = {
                "search_query": song,
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
            song_name = os.path.splitext(filename)[0]
            
            # Try to read MP3 metadata if mutagen is available
            if EasyID3 and filename.lower().endswith('.mp3'):
                try:
                    audio = MP3(file_path, ID3=EasyID3)
                    title = audio.get('title', [None])[0]
                    artist = audio.get('artist', [None])[0]
                    if title and artist:
                        song_name = f"{title} - {artist}"
                    elif title:
                        song_name = title
                except Exception:
                    pass # Fallback to filename on error
            
            songs.append(song_name)
            print(f"  Found: {song_name}")
    return songs

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
                messagebox.showinfo("Success", f"Playlist URL copied to clipboard!\n\n{playlist_url}")
            else:
                messagebox.showwarning("Warning", "No videos found.")

    btn_select = tk.Button(root, text="Select Folder", command=on_select_folder, height=2, width=20)
    btn_select.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    create_ui()