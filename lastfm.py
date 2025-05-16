from keys import *
import deezer

# --- last.fm get reccomendations-----------------------------

network = deezer.LastFMNetwork(
    api_key=LASTFM_API_KEY,
    api_secret=LASTFM_API_SECRET
)

track = network.get_track('Noisia', 'Dead Limit')
track.streamable

track.get_listener_count()
track.get_cover_image()
track.get_artist()
track.get_album()
track.get_title()
track.get_duration()
track.get_mbid()
track.get_similar()
track.get_title()
track.get_url()