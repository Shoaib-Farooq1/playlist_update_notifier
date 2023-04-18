import spotipy
from spotipy.oauth2 import SpotifyOAuth
import http.server
import socketserver
import os
import html
import datetime

# Set up Spotify authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="e501baae52844189a871b12a3f605b2c",
                                               client_secret="9bcd7d669a4540e58a67c5312edc5158",
                                               redirect_uri="http://localhost:8000/callback",
                                               scope="user-library-read"))

# Set initial values for pagination
offset = 0
limit = 50

# Prompt user for time constraint
days = input("Enter the number of days to check for updated playlists (default is 7): ")
try:
    days = int(days)
except ValueError:
    days = 7

# Get user's saved tracks
tracks = []
while True:
    results = sp.current_user_saved_tracks(limit=limit, offset=offset)
    tracks.extend(results["items"])
    offset += limit
    if len(results["items"]) == 0:
        break

# Get the IDs of the tracks
track_ids = [track["track"]["id"] for track in tracks if track["track"] is not None and track["track"]["id"] is not None]

# Get the IDs of the user's playlists
playlist_ids = [playlist["id"] for playlist in sp.current_user_playlists()["items"]]

# Get the intersection of the track IDs and playlist IDs
playlist_track_ids = []
for playlist_id in playlist_ids:
    playlist_track_ids.extend([playlist_track["track"]["id"] for playlist_track in sp.playlist_items(playlist_id)["items"] if playlist_track["track"] is not None and playlist_track["track"]["id"] is not None])
common_track_ids = set(track_ids) & set(playlist_track_ids)

# Get the playlists containing the common track IDs and their last modified dates
playlist_data = []
for playlist_id in playlist_ids:
    results = sp.playlist_items(playlist_id)
    playlist_track_ids = set([playlist_track["track"]["id"] for playlist_track in results["items"] if playlist_track["track"] is not None and playlist_track["track"]["id"] is not None])
    common_ids = common_track_ids & playlist_track_ids
    if len(common_ids) > 0:
        name = html.escape(sp.playlist(playlist_id)["name"])
        image_url = sp.playlist(playlist_id)["images"][0]["url"]
        playlist_url = sp.playlist(playlist_id)["external_urls"]["spotify"]
        last_modified = None
        for item in results['items']:
            if item['track']['id'] in common_ids:
                track_created_at = datetime.datetime.fromisoformat(item['added_at'][:-1])
                if last_modified is None or track_created_at > last_modified:
                    last_modified = track_created_at
        if last_modified is None:
            last_modified = sp.playlist(playlist_id).get('last_modified')
            if last_modified is not None:
                try:
                    last_modified = datetime.datetime.fromisoformat(last_modified.split(":")[1][:-1])
                except IndexError:
                    print(f"Error: Could not parse last modified date for playlist '{name}'")
                    continue
            else:
                continue
        playlist_data.append((name, image_url, playlist_url, last_modified.strftime("%Y-%m-%d %H:%M:%S")))

print(f"Retrieved {len(playlist_ids)} playlists.")
print(f"Found {len(playlist_data)} playlists modified in the last {days} days.")

# Create a simple HTTP server to display the playlist names, images, and last modified dates
PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler

# Sort playlist data by last modified date in ascending order
playlist_data.sort(key=lambda x: datetime.datetime.strptime(x[3], "%Y-%m-%d %H:%M:%S"))

# Create a temporary index.html file with the playlist names, images, and last modified dates
with open('index.html', 'w', encoding='utf-8') as f:
    f.write('<html><head><style>body {background-color: #222; color: #ddd;} div {float:left; margin:20px; background-color:#333; border-radius: 5px; box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2); transition: 0.3s;} div:hover {box-shadow: 0 8px 16px 0 rgba(0, 0, 0, 0.2);} h2 {font-size: 20px; font-weight: bold; margin: 10px;} img {width: 200px; height: 200px;} a {text-decoration: none; color: #ddd;} </style></head><body>')
    if len(playlist_data) > 0:
        for name, image_url, playlist_url, last_modified in playlist_data:
            f.write(f'<div><a href="{playlist_url}" target="_blank"><img src="{image_url}" alt="{name}"><h2>{name}</h2><p>Last Modified: {last_modified}</p></a></div>')
    else:
        f.write('<h2>No playlists modified in the last 7 days.</h2>')
    f.write('</body></html>')


# Start the server
os.chdir(os.path.dirname(os.path.abspath(__file__)))
httpd = socketserver.TCPServer(("", PORT), Handler)
print(f"Serving at http://localhost:{PORT}")
httpd.serve_forever()