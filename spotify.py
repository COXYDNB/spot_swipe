import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import os
import requests
import re
import csv
from keys import *

# --- Spotify Auth Setup ---
SCOPE = "playlist-read-private playlist-modify-private playlist-modify-public user-library-read user-read-currently-playing user-read-playback-state user-modify-playback-state"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SCOPE
))


# other functions -------------------------------------------------------------

def safe_filename(name):
    return re.sub(r'[^\w\-]', '_', name)  # Replace anything not a letter, digit, or underscore/hyphen

def download_image(user_id, url, filename, folder='playlist_images'):
    if not os.path.exists(folder):
        os.makedirs(folder)

    if not os.path.exists(f"{folder}/{user_id}"):
        os.makedirs(f"{folder}/{user_id}")

    filepath = os.path.join(folder, user_id, f"{filename}.jpg")

    if os.path.exists(filepath):
        print(f"{filename}.jpg already exists, skipping download.")
        return

    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded {filename}.jpg")
    else:
        print(f"Failed to download image: {url}")

def upsert_to_csv(data, csv_file, unique_keys):
    """
    Upsert a list of dictionaries into a CSV file.

    Parameters:
    - data (list of dict): Records to be inserted/updated.
    - csv_file (str): Path to the CSV file.
    - unique_keys (str or list of str): Key(s) that define uniqueness.
    """
    if isinstance(unique_keys, str):
        unique_keys = [unique_keys]  # Convert to list if it's a string

    def get_key(record):
        return tuple(record[k] for k in unique_keys)

    rows = []
    existing_keys = {}

    # Read existing rows
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = get_key(row)
                existing_keys[key] = row

    # Update or add new records
    for record in data:
        key = get_key(record)
        existing_keys[key] = record  # This replaces existing or adds new

    # Write all records
    if existing_keys:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = list(next(iter(existing_keys.values())).keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_keys.values())

# --- Spotify functions -------------------------------------------------------

def store_user(user, csv_file='users.csv'):
    user_row = {
        'user_id': user['id'],
        'display_name': user['display_name'],
        'external_url': user['external_urls']['spotify'],
        'followers': user['followers']['total'],
        'image_url': user['images'][0]['url'] if user.get('images') else None
    }

    upsert_to_csv([user_row], csv_file=csv_file, unique_keys=['user_id'])

def get_store_playlists(user_id, csv_file = 'playlists.csv', img_folder='playlist_images'):
    all_playlists = []
    results = sp.current_user_playlists(limit=50)
    all_playlists.extend(results['items'])

    # Continue fetching while there's a next page
    while results['next']:
        results = sp.next(results)
        all_playlists.extend(results['items'])

    user_playlists = [
        {
            'user_id': user_id,
            'playlist_id': p['id'],
            'name': p['name'],
            'image_url': p['images'][0]['url'] if p['images'] else None,
            'track_count': p['tracks']['total']
        }
        for p in all_playlists
        if p['owner']['id'] == user_id
    ]

    upsert_to_csv(user_playlists, csv_file=csv_file, unique_keys=['playlist_id'])

    # Download images
    for p in user_playlists:
        if p['image_url']:
            download_image(user_id=user_id, url=p['image_url'], filename=p['playlist_id'], folder=img_folder)

    return user_playlists

def get_store_tracks(user_id, playlist_id, img_folder = 'album_images'):

    all_tracks = []
    results = sp.playlist_items(playlist_id, limit=100)
    all_tracks.extend(results['items'])

    # Continue fetching while there's a next page
    while results['next']:
        results = sp.next(results)
        all_tracks.extend(results['items'])

    # Store Albums ---------------------------

    albums = {
            t['track']['album']['id']: {
                'album_id': t['track']['album']['id'],
                'album_name': t['track']['album']['name'],
                'album_type': t['track']['album']['type'],
                'release_date': t['track']['album']['release_date'],
                'spotify_url': t['track']['album']['external_urls']['spotify'],
                'image_url': t['track']['album']['images'][0]['url'],
                'total_tracks': t['track']['album']['total_tracks']
        }
        for t in all_tracks
        if t['is_local'] == False
    }

    distinct_albums = list(albums.values())

    upsert_to_csv(distinct_albums, csv_file='albums.csv', unique_keys=['album_id'])

    # Store Artists ----------------------------

    artists = {
        artist['id']: {
            'artist_id': artist['id'],
            'artist_name': artist['name'],
            'artist_url': artist['external_urls']['spotify']
        }
        for r in all_tracks
        if r['is_local'] == False
        for artist in r['track']['album']['artists']
    }

    distinct_artists = list(artists.values())

    upsert_to_csv(distinct_artists, csv_file='artists.csv', unique_keys=['artist_id'])

    # Store Tracks -----------------------------

    tracks = {
        t['track']['id']: {
                'track_id': t['track']['id'],
                'track_name': t['track']['name'],
                'duration_ms': t['track']['duration_ms'],
                'popularity': t['track']['popularity'],
                'spotify_url': t['track']['external_urls']['spotify'],
                'isrc': t['track']['external_ids']['isrc']
            }
            for t in all_tracks
            if t['is_local'] == False
    }

    distinct_tracks = list(tracks.values())

    upsert_to_csv(distinct_tracks, csv_file='tracks.csv', unique_keys=['track_id'])

    # Store Playlist_Tracks --------------------

    playlists_tracks = list({
        (playlist_id, t['track_id']) for t in distinct_tracks
    })
    # Convert back to dicts if needed
    distinct_playlist_tracks = [
        {'playlist_id': p, 'track_id': t}
        for p, t in playlists_tracks
    ]

    upsert_to_csv(distinct_playlist_tracks, 'playlists_tracks.csv', unique_keys=['playlist_id', 'track_id'])

    # Store Artists_Tracks -----------------------

    artists_tracks = list({
        (artist['id'], track['id'])
        for t in all_tracks
        for artist in t['track']['album']['artists']
        if (track := t['track'])  # Python 3.8+ walrus operator
    })

    distinct_artists_tracks = [
        {'artist_id': a, 'track_id': t}
        for a, t in artists_tracks
    ]

    upsert_to_csv(distinct_artists_tracks, 'artists_tracks.csv', unique_keys=['artist_id', 'track_id'])

    # Store Album_Tracks -----------------------

    albums_tracks = list({
        (t['track']['album']['id'], t['track']['id'])
        for t in all_tracks
    })

    distinct_albums_tracks = [
        {'album_id': a, 'track_id': t}
        for a, t in albums_tracks
    ]

    upsert_to_csv(distinct_albums_tracks, 'albums_tracks.csv', unique_keys=['album_id', 'track_id'])


    # Store Artists_Albums ------------------------

    artists_albums = list({
        (artist['id'], album['id'])
        for t in all_tracks
        for artist in t['track']['album']['artists']
        if (album := t['track']['album'])  # Python 3.8+ walrus operator
    })

    distinct_artists_albums = [
        {'artist_id': a, 'album_id': al}
        for a, al in artists_albums
    ]

    # download album art
    for a in distinct_albums:
        if a['image_url']:
            download_image(user_id=user_id, url=a['image_url'], filename=a['album_id'], folder=img_folder)

    upsert_to_csv(distinct_artists_albums, 'albums_artists.csv', unique_keys=['artist_id', 'album_id'])
