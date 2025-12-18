import base64
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
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI") or  "https://spotify-to-musify.vercel.app/"




def get_new_access_token():
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

    auth_header = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode()

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=10,
    )

    response.raise_for_status()
    return response.json()["access_token"]

SPOTIFY_ACCESS_TOKEN = get_new_access_token()


def export_playlist(playlist_id):
   
    sp = spotipy.Spotify(auth=SPOTIFY_ACCESS_TOKEN)
    # auth_manager = spotipy.Spotify(auth_manager=SpotifyOAuth(
    #     client_id=CLIENT_ID,
    #     client_secret=CLIENT_SECRET,
    #     redirect_uri=REDIRECT_URI,
    #     scope="playlist-read-private",
    #     cache_handler=None 
    # ))
    # auth_manager.refresh_access_token(os.getenv("SPOTIFY_REFRESH_TOKEN"))
    # sp = spotipy.Spotify(auth_manager=auth_manager)
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