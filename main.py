import os
from flask import Flask, session, redirect, url_for, request, render_template
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from flask import jsonify
app = Flask(__name__, template_folder='C:/Users/vova2/PycharmProjects/SpotifyMusic')
app.config['SECRET_KEY'] = os.urandom(64)  # Fixed key name

client_id = '35b9e497c11d4762a1c0e8079c35471e'
client_secret = 'e3ade5f52df24d8ab14ded88cea867c3'
redirect_uri = 'http://localhost:5000/callback'
scope = 'user-library-read'

cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler
)
sp = Spotify(auth_manager=sp_oauth)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/authorization')
def authorize():
    token_info = cache_handler.get_cached_token()
    if not sp_oauth.validate_token(token_info):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    else:
        return redirect(url_for('dashboard'))

@app.route('/playlists-data')
def playlists_data():
    token_info = cache_handler.get_cached_token()
    if not token_info:
        return redirect(url_for('home'))
    
    sp = Spotify(auth_manager=sp_oauth)
    playlists = sp.current_user_playlists()
    
    playlist_data = []
    for playlist in playlists['items']:
        playlist_data.append({
            'name': playlist['name'],
            'id': playlist['id']
        })
    
    return jsonify(playlist_data)


@app.route('/callback')
def callback():
    code = request.args.get('code')
    sp_oauth.get_access_token(code, as_dict=False)
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    token_info = cache_handler.get_cached_token()
    if not token_info:
        return redirect(url_for('home'))
    
    sp = Spotify(auth_manager=sp_oauth)
    playlists = sp.current_user_playlists()
    
    return render_template('dashboard.html', 
                           playlists=playlists['items'])




@app.route('/liked-tracks-data')
def liked_tracks_data():
    token_info = cache_handler.get_cached_token()
    if not token_info:
        return redirect(url_for('home'))
    
    sp = Spotify(auth_manager=sp_oauth)
    
    # Get user's saved tracks (limit to 20)
    results = sp.current_user_saved_tracks(limit=20)
    
    # Convert to a format suitable for JSON
    tracks_data = []
    for item in results['items']:
        track = item['track']
        tracks_data.append({
            'name': track['name'],
            'artists': ', '.join(artist['name'] for artist in track['artists']),
            'id': track['id']
        })
    
    return jsonify(tracks_data)





if __name__ == '__main__':
    app.run(debug=True)

