import queue
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

video_queue = queue.Queue()
current_song_data = None
playlist_for_display = []

# --- New global variable to store the request page address ---
request_page_address = None

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

@app.route("/video_ended", methods=["GET"])
def handle_video_ended():
    global current_song_data
    
    current_song_data = None
    
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

@app.route("/video_error", methods=["GET"])
def handle_video_error():
    global current_song_data

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
        return handle_video_ended()

@app.route("/get_playlist_status", methods=["GET"])
def get_playlist_status():
    return jsonify({"playlist": playlist_for_display})

# --- New routes to manage the request page address ---
@app.route("/set_request_address", methods=["POST"])
def set_request_address():
    global request_page_address
    request_page_address = request.json.get("address")
    print(f"Request page address set to: {request_page_address}")
    return jsonify({"success": True})

@app.route("/get_request_address", methods=["GET"])
def get_request_address():
    if request_page_address:
        return jsonify({"address": request_page_address})
    else:
        return jsonify({"address": "Not loaded"})

@app.route("/", methods=["GET"])
def display_page():
    return render_template("jukebox_display.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5001)