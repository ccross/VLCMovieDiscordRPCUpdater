#!/usr/bin/env python3

import json
import re
import time
import requests
from pypresence import Presence

# Load configuration from JSON file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

client_id = config['discord_client_id']
vlc_http_host = config['vlc_http_host']
vlc_http_port = config['vlc_http_port']
vlc_http_password = config['vlc_http_password']
omdb_api_key = config['omdb_api_key']

RPC = Presence(client_id)
RPC.connect()

# Variable to track the last processed filename
last_filename = None
current_presence_data = None

def get_vlc_status():
    try:
        response = requests.get(
            f'http://{vlc_http_host}:{vlc_http_port}/requests/status.json',
            auth=('', vlc_http_password)
        )
        status = response.json()
        return status
    except Exception as e:
        print(f"Error fetching VLC status: {e}")
        return None

def extract_movie_info_from_filename(filename):
    # Regular expression to match the filename format, with optional {Edition-VERSION} part
    pattern = r"(.+) \((\d{4})\)\.\w+(?:\s*\{.*\})?\.mkv"
    match = re.match(pattern, filename)
    if match:
        title = match.group(1)
        year = match.group(2)
        return title, year
    return None, None

def get_movie_info(title, year):
    try:
        response = requests.get(f'http://www.omdbapi.com/?t={title}&y={year}&apikey={omdb_api_key}')
        movie_info = response.json()
        if movie_info.get('Response') == 'True':
            return movie_info
        else:
            print(f"Error fetching movie info: {movie_info.get('Error')}")
            return None
    except Exception as e:
        print(f"Error fetching movie info: {e}")
        return None

def update_presence(status):
    global last_filename, current_presence_data

    if status and status.get('state') == 'playing':
        info = status.get('information', {})
        meta = info.get('category', {}).get('meta', {})
        filename = meta.get('filename', 'Unknown')

        # Check if the filename has changed
        if filename != last_filename:
            last_filename = filename
            title, year = extract_movie_info_from_filename(filename)
            if title and year:
                movie_info = get_movie_info(title, year)
                if movie_info:
                    movie_title = movie_info.get('Title', 'Unknown')
                    movie_year = movie_info.get('Year', 'Unknown')
                    movie_director = movie_info.get('Director', 'Unknown')
                    movie_genre = movie_info.get('Genre', 'Unknown')
                    imdb_id = movie_info.get('imdbID', '')
                    poster_url = movie_info.get('Poster', '')

                    details = f"Watching: {movie_title} ({movie_year})"
                    state = f"Directed by {movie_director} | {movie_genre}"

                    # Construct Letterboxd URL
                    letterboxd_url = f"https://letterboxd.com/imdb/{imdb_id}/"

                    current_presence_data = {
                        "details": details[:128],
                        "state": state[:128],
                        "large_image": poster_url,  # Use the poster URL from OMDb
                        "large_text": movie_title,  # Movie title as tooltip
                        "small_image": "https://ccross.github.io/VLCMovieDiscordRPCUpdater/movie.png",  # Playing icon
                        "small_text": movie_title,  # Movie title as tooltip
                        "start": int(time.time()),
                        "buttons": [{"label": "View on Letterboxd", "url": letterboxd_url}]
                    }
                else:
                    # Fallback to using title and year from filename
                    details = f"Watching: {title} ({year})"
                    current_presence_data = {
                        "details": details[:128],
                        "state": "No additional info available",
                        "large_image": "https://example.com/large_image.png",  # Replace with your large image URL
                        "large_text": title,  # Movie title as tooltip
                        "small_image": "https://ccross.github.io/VLCMovieDiscordRPCUpdater/movie.png",  # Playing icon
                        "small_text": title,  # Movie title as tooltip
                        "start": int(time.time())
                    }
            else:
                current_presence_data = {
                    "details": "Watching a movie",
                    "state": "Filename format not recognized",
                    "large_image": "https://example.com/large_image.png",  # Replace with your large image URL
                    "large_text": "",  # Empty large text
                    "small_image": "https://ccross.github.io/VLCMovieDiscordRPCUpdater/movie.png",  # Playing icon
                    "small_text": "Unknown Movie",  # Unknown movie title as tooltip
                    "start": int(time.time())
                }

        # Update presence with current data
        if current_presence_data:
            RPC.update(**current_presence_data)

    else:
        RPC.update(
            details="VLC is idle",
            state="No media playing",
            large_image="https://example.com/large_image.png",  # Replace with your large image URL
            large_text="",  # Empty large text
            small_image="https://ccross.github.io/VLCMovieDiscordRPCUpdater/stop.png",  # Stopped icon
            small_text="Nothing Playing",
            start=int(time.time())
        )

# Main loop to update presence
try:
    while True:
        status = get_vlc_status()
        update_presence(status)
        time.sleep(20)  # Update every 20 seconds
except KeyboardInterrupt:
    pass
finally:
    RPC.close()
