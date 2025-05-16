from spotify import *
import duckdb
import glob

# INIT SPOTIFY -----------------------------------------------

# Get spotify user
user = sp.current_user()

# store user details
store_user(user, csv_file = 'users.csv')

# get user's playlists, playlist art
playlists = get_store_playlists(user_id=user['id'], csv_file='playlists.csv', img_folder='playlist_images')

# get tracks, track art, albums, all relationships
for p in playlists:
    print(f"Storing playist: {p['name']}")
    get_store_tracks(user_id = user['id'], playlist_id=p['playlist_id'], img_folder='album_images')

# DuckDB ------------------------------

con = duckdb.connect(database = "data.db")

csv_files = glob.glob('*.csv')

for file in csv_files:
    con.execute(f"""
    CREATE TABLE {file.removesuffix('.csv')} AS 
    SELECT * FROM read_csv_auto({file})
""")

result = con.sql("""
    SELECT artist_name, track_name, popularity, t.spotify_url, al.image_url FROM artists a
                 
    JOIN artists_tracks at ON a.artist_id = at.artist_id
    JOIN tracks t ON at.track_id = t.track_id

    LEFT JOIN albums_tracks alt on t.track_id = alt.track_id
    JOIN albums al on alt.album_id = al.album_id                

    WHERE artist_name = 'Coxy'
    """)

print(result)
result = result.fetchdf()

result = con.sql("""
    SELECT artist_name, COUNT(at.track_id) as 'saved_tracks' FROM artists a
                 
    LEFT JOIN  artists_tracks at ON at.artist_id = a.artist_id
                 
    WHERE NOT artist_name = 'Various Artists'
                 
    GROUP BY a.artist_name
                 
    ORDER BY COUNT(at.track_id) desc
                 
    """)

print(result)
result = result.fetchdf()

# Option A: Fetch as pandas DataFrame and print (pretty table)

