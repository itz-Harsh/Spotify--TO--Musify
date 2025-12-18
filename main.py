import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os , requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

app = FastAPI(
    title="Spotify Playlist Exporter API",
    description="Export Spotify playlists for Musify using FastAPI + Spotipy",
    version="1.0.0"
)

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = "https://spotify-to-musify.vercel.app/"

def export_playlist(playlist_id):
    """
    Exports a Spotify playlist's tracks to a CSV file.
    """

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="playlist-read-private"
    ))

    tracks = []
    results = sp.playlist_tracks(playlist_id)
    for item in results['items']:
        track = item['track']
        tracks.append(track["name"] + " " + track["album"]["name"])
        
    if not tracks:
        print("No tracks found or unable to access playlist.")
        return
    
    return tracks



@app.get("/")
def home():
    return {"status": "API is Fine !"}


@app.get("/api/{url}")
def convert(url : str):
    
    try:
        data = []
        playlist_id = url.split("/")[-1].split("?")[0]
        tracks = export_playlist(playlist_id)
        if tracks is None:
            raise HTTPException(status_code=404, detail="Playlist not found or inaccessible.")
        
        for track in tracks:
            raw = requests.get(f"https://saavn.sumit.co/api/search?query={track}")
            song_data = raw.json().get("data").get("topQuery")
            data.append(song_data)
        
        return {"data": data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




if __name__ == '__main__':
    app.run(debug=True)