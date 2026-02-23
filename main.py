import base64
import os
import asyncio
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

load_dotenv()

today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

app = FastAPI(
    title="Spotify Playlist Exporter API",
    description="Export Spotify playlists for Musify using FastAPI + Async",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://musify-harsh.vercel.app",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# 🔐 SPOTIFY TOKEN REFRESH
# --------------------------------------------------

async def get_new_access_token():
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

    auth_header = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )

        response.raise_for_status()
        return response.json()["access_token"]


# --------------------------------------------------
# 🎵 GET PLAYLIST DETAILS
# --------------------------------------------------

async def get_playlist_details(playlist_id, access_token):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"

    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        res.raise_for_status()
        return res.json()


# --------------------------------------------------
# 🎶 EXTRACT TRACK NAMES
# --------------------------------------------------

def export_playlist(raw_tracks):
    tracks = []

    for item in raw_tracks.get("items", []):
        song = item.get("track")
        if not song:
            continue

        name = song.get("name", "").split("(")[0]
        artist = song.get("artists", [{}])[0].get("name", "")
        tracks.append(f"{name} {artist}")

    return tracks


# --------------------------------------------------
# 🚀 CONCURRENT JIOSAAVN FETCH
# --------------------------------------------------

semaphore = asyncio.Semaphore(10)  # limit concurrency

async def fetch_song(client, track):
    async with semaphore:
        try:
            # search
            search_res = await client.get(
                "https://jiosaavn-api-dc21.onrender.com/api/search",
                params={"query": track},
                timeout=20
            )

            song_data = search_res.json().get("data", {}).get("songs", {}).get("results", [])
            if not song_data:
                return None

            song_id = song_data[0].get("id")
            if not song_id:
                return None

            # get details
            song_res = await client.get(
                f"https://jiosaavn-api-dc21.onrender.com/api/songs/{song_id}",
                timeout=20
            )

            return song_res.json().get("data", [])[0]

        except Exception:
            return None


# --------------------------------------------------
# 🌐 ROUTES
# --------------------------------------------------

@app.get("/")
async def home():
    return {"status": "API is Fine !"}


@app.get("/api/{playlist_id}")
async def convert(playlist_id: str):
    start = datetime.now()

    try:
        access_token = await get_new_access_token()
        print(access_token)
        raw_playlist = await get_playlist_details(playlist_id, access_token)

        tracks = export_playlist(raw_playlist.get("tracks", {}))
        if not tracks:
            raise HTTPException(status_code=404, detail="Playlist not found or empty.")

        name = raw_playlist.get("name")
        image = raw_playlist.get("images", [{}])[0].get("url")

        async with httpx.AsyncClient(timeout=20) as client:
            tasks = [fetch_song(client, track) for track in tracks]
            results = await asyncio.gather(*tasks)

        songs = [song for song in results if song]

        end = datetime.now()
        print("Execution time:", (end - start).total_seconds(), "seconds")

        return {
            "success": True,
            "data": {
                "name": name,
                "type": "playlist",
                "year": today,
                "image": image,
                "songs": songs
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# ▶ RUN SERVER
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
