import base64
import os , requests , time 
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
load_dotenv()


app = FastAPI(
    title="Spotify Playlist Exporter API",
    description="Export Spotify playlists for Musify using FastAPI + Spotipy",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",        # Vite
        "http://localhost:3000",        # React
        "https://musify-harsh.vercel.app",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

def export_playlist(track):
   
    tracks = []
    
    for item in track['items']:
        song = item['track']
        tracks.append(song["name"].split("(")[0] + " " + song["artists"][0]["name"])
        
    if not tracks:
        print("No tracks found or unable to access playlist.")
        return

    return tracks


def get_playlist_details(playlist_id, access_token= SPOTIFY_ACCESS_TOKEN):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    res = requests.get(url, headers=headers)
    res.raise_for_status()

    return res.json()



@app.get("/")
def home():
    return {"status": "API is Fine !"}



@app.get("/api/{_id}")
def convert(_id : str):
    start = time.time()
    try:
        data = [] 
        raw = get_playlist_details(_id)
        
        tracks = export_playlist(raw.get("tracks"))
        
        name = raw.get("name") 
        image = raw.get("images")[0].get("url")
        # return { name , image}
        if tracks is None:
            raise HTTPException(status_code=404, detail="Playlist not found or inaccessible.")
        
        
        for track in tracks:
            raw = requests.get(f"https://jiosaavn-api-dc21.onrender.com/api/search?query={track}")
            song_data = raw.json().get("data").get("songs").get("results")
            id = song_data[0].get("id") if song_data else None
            
            if id is None:
                continue
            songs = requests.get(f"https://jiosaavn-api-dc21.onrender.com/api/songs/{id}")
            song_info = songs.json().get("data")[0]
            data.append(song_info)
            
        end = time.time()
        print(f"Execution time: {end - start} seconds")

        return {
            "success" : True,
            "data" : {
                "name" : name,
                "type" : "playlist",
                "year" : today,
                "image" : image,
                "songs" : data
            }
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    app.run(debug=True)
