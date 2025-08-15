import queue
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

video_queue = queue.Queue()
current_song_data = None
playlist_for_display = []

@app.route("/add_to_queue", methods=["POST"])
def add_to_queue():
    video_ids = request.json.get("video_ids")
    title = request.json.get("title")
    if not video_ids or not title:
        return jsonify({"success": False, "error": "Missing video IDs or title."}), 400
    
    song_data_for_queue = {"video_ids": video_ids, "title": title}
    video_queue.put(song_data_for_queue)
    playlist_for_display.append(title)
    
    print(f"Added song '{title}' with {len(video_ids)} candidates to queue.")
    return jsonify({"success": True, "message": f"Added video {title} to queue."})

# --- NEW ROUTE for video end event ---
@app.route("/video_ended", methods=["GET"])
def handle_video_ended():
    global current_song_data
    
    # After a video ends, we should move to the next user-requested song
    current_song_data = None # Reset the current song state
    
    if not video_queue.empty():
        next_song = video_queue.get()
        current_song_data = {
            'title': next_song['title'],
            'video_ids': next_song['video_ids'],
            'candidate_index': 0
        }
        
        if playlist_for_display:
            try:
                playlist_for_display.remove(next_song['title'])
            except ValueError:
                pass
        
        print(f"Video ended. Now attempting new song: '{current_song_data['title']}' from candidate 0.")
        current_video_id = current_song_data['video_ids'][current_song_data['candidate_index']]
        return jsonify({
            "success": True,
            "video_id": current_video_id,
            "title": current_song_data['title']
        })
    else:
        print("Video ended. Queue is empty.")
        return jsonify({"success": False, "message": "Queue is empty."})

# --- NEW ROUTE for player errors ---
@app.route("/video_error", methods=["GET"])
def handle_video_error():
    global current_song_data

    # If there's an error, try the next fallback for the current song
    if current_song_data and current_song_data['candidate_index'] < len(current_song_data['video_ids']) - 1:
        current_song_data['candidate_index'] += 1
        print(f"Error occurred. Retrying '{current_song_data['title']}' with candidate {current_song_data['candidate_index']}.")
        
        current_video_id = current_song_data['video_ids'][current_song_data['candidate_index']]
        return jsonify({
            "success": True,
            "video_id": current_video_id,
            "title": current_song_data['title']
        })
    else:
        # No fallbacks left for the current song, so move to the next song
        return handle_video_ended() # Reuse the logic for getting the next song

@app.route("/get_playlist_status", methods=["GET"])
def get_playlist_status():
    return jsonify({"playlist": playlist_for_display})

@app.route("/", methods=["GET"])
def display_page():
    return render_template("jukebox_display.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5001)