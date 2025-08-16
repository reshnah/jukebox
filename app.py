import os
import requests
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from yt_dlp import YoutubeDL

# Configure Google Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)

DISPLAY_SERVER_URL = "http://127.0.0.1:5001"
playlist = []

def search_youtube_ids(query, max_results=10):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch', # Search multiple results
        'noplaylist': True,
        'extract_flat': True, # Faster search, don't download full info
        'skip_download': True,
        'force_generic_extractor': True, # Important for some URLs
        #'match_filter': yt_dlp.utils.match_filter_func('is_live!=True'), # Exclude live streams
        'max_downloads': max_results # Get up to max_results video candidates
    }

    video_ids = []
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f'ytsearch{max_results}:{query}', download=False)
            if info and 'entries' in info:
                for entry in info['entries']:
                    if 'id' in entry:
                        video_ids.append(entry['id'])
        except Exception as e:
            print(f"Error searching YouTube with yt-dlp for '{query}': {e}")
            
    return video_ids

@app.route("/", methods=["GET"])
def index():
    request_address = f"http://{request.host}"
    # As soon as a user accesses this page, send its address to the display
    try:
        requests.post(f"{DISPLAY_SERVER_URL}/set_request_address", json={"address": request_address})
    except requests.exceptions.RequestException as e:
        print(f"Could not set request address on display server: {e}")
        
    return render_template("request_songs.html")

@app.route("/add_song", methods=["POST"])
def add_song():
    user_input = request.json.get("user_input")
    if not user_input:
        return jsonify({"success": False, "error": "No user input provided."}), 400

    model = genai.GenerativeModel('gemma-3-27b-it')
    prompt = f"The user wants to play a song on a jukebox. They said: '{user_input}'. Please respond with *only* the song title and artist that best matches their request. For example, if they say 'play something by the beatles', you should respond 'Hey Jude by The Beatles'."

    try:
        response = model.generate_content(prompt)
        song_title = response.text.strip()
        
        if song_title:
            video_ids = search_youtube_ids(song_title)
            if video_ids:
                # Also send the request page address to the display server
                requests.post(f"{DISPLAY_SERVER_URL}/add_to_queue", json={"video_ids": video_ids, "title": song_title})
                
                playlist.append({"title": song_title, "video_ids": video_ids})

                return jsonify({"success": True, "playlist": [s['title'] for s in playlist]})
            else:
                return jsonify({"success": False, "error": f"Could not find any videos for '{song_title}'."}), 500
        else:
            return jsonify({"success": False, "error": "Could not determine song from your request."}), 500
    except Exception as e:
        print(f"Gemini API error: {e}")
        return jsonify({"success": False, "error": "An error occurred with the AI service."}), 500

@app.route("/get_playlist", methods=["GET"])
def get_playlist():
    try:
        response = requests.get(f"{DISPLAY_SERVER_URL}/get_playlist_status")
        return jsonify(response.json())
    except requests.exceptions.RequestException:
        return jsonify({"playlist": ["Jukebox is offline..."]})

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)