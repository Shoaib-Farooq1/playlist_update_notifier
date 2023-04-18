import spotipy
from spotipy.oauth2 import SpotifyOAuth
import http.server
import socketserver
import os
import html
import datetime

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="e501baae52844189a871b12a3f605b2c", client_secret="9bcd7d669a4540e58a67c5312edc5158", redirect_uri="http://localhost:8000/callback", scope="playlist-read-private"))

# Set initial values for pagination
offset = 0
limit = 50

# Prompt user for time constraint
days = input("Enter the number of days to check for updated playlists (default is 7): ")
try:
    days = int(days)
except ValueError:
    days = 7

# Get user's playlists
playlists = []
while True:
    results = sp.current_user_playlists(limit=limit, offset=offset)
    playlists.extend(results["items"])
    offset += limit
    if len(results["items"]) == 0:
        break

# Sort playlists by most recently updated
playlists.sort(key=lambda playlist: playlist.get('tracks', {}).get('total', 0), reverse=True)

# Get playlist names, image URLs, and last modified dates
playlist_data = []
for playlist in playlists:
    name = html.escape(playlist['name'])
    image_url = playlist['images'][0]['url']
    playlist_url = playlist['external_urls']['spotify']
    last_modified = None
    results = sp.playlist_items(playlist['id'], fields="items(added_at, track(name, album(release_date)))")
    print(f"Playlist: {name}")
    latest_track_created_at = None
    for item in results['items']:
        track_created_at = datetime.datetime.fromisoformat(item['added_at'][:-1])
        if latest_track_created_at is None or track_created_at > latest_track_created_at:
            latest_track_created_at = track_created_at
    if latest_track_created_at is None:
        last_modified = playlist.get('last_modified')
        if last_modified is not None:
            try:
                last_modified = datetime.datetime.fromisoformat(last_modified.split(":")[1][:-1])
            except IndexError:
                print(f"Error: Could not parse last modified date for playlist '{name}'")
                continue
        else:
            continue
    else:
        last_modified = latest_track_created_at
    time_since_modified = datetime.datetime.now() - last_modified
    if time_since_modified > datetime.timedelta(days=days):
        continue
    playlist_data.append((name, image_url, playlist_url, last_modified.strftime("%Y-%m-%d %H:%M:%S")))

print(f"Retrieved {len(playlists)} playlists.")
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