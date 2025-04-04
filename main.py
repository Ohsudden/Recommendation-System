import os
from flask import Flask, session, redirect, url_for, request, render_template, jsonify
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from analysis_function import AudioProcessor
from datetime import timedelta

class SpotifyFlaskApp:
    
    def __init__(self):
        self.app = Flask(__name__, template_folder='C:/Users/vova2/PycharmProjects/SpotifyMusic')
        self.app.config['SECRET_KEY'] = os.urandom(64)
        self.app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
        self.app.config['SESSION_PERMANENT'] = True
        self.client_id = '35b9e497c11d4762a1c0e8079c35471e'
        self.client_secret = 'e3ade5f52df24d8ab14ded88cea867c3'
        self.redirect_uri = 'http://localhost:5000/callback'
        self.scope = 'user-library-read'
        
        self.cache_handler = FlaskSessionCacheHandler(session)
        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            cache_handler=self.cache_handler
        )
        self.sp = Spotify(auth_manager=self.sp_oauth)
        
        self.register_routes()
    
    def register_routes(self):
        """Register all route handlers with the Flask app."""
        self.app.route('/', endpoint='home')(self.home)
        self.app.route('/authorization', endpoint='authorize')(self.authorize)
        self.app.route('/playlists-data', endpoint='playlists_data')(self.playlists_data)
        self.app.route('/callback', endpoint='callback')(self.callback)
        self.app.route('/dashboard', endpoint='dashboard')(self.dashboard)
        self.app.route('/liked-tracks-data', endpoint='liked_tracks_data')(self.liked_tracks_data)
        self.app.route('/recommend/<playlist_id>', endpoint='recommend')(self.recommend)
        self.app.route('/recommend-by-recent-songs/', endpoint='recommend_by_recent_songs')(self.recommend_by_recent_songs)

    
    def home(self):
        """Render the home page."""
        return render_template('index.html')
    
    def authorize(self):
        """Authorize the user with Spotify."""
        token_info = self.cache_handler.get_cached_token()
        if not self.sp_oauth.validate_token(token_info):
            auth_url = self.sp_oauth.get_authorize_url()
            return redirect(auth_url)
        else:
            return redirect(url_for('dashboard'))
    
    def playlists_data(self):
        """Return user's playlists as JSON."""
        token_info = self.cache_handler.get_cached_token()
        if not token_info:
            return redirect(url_for('home'))
        
        sp = Spotify(auth_manager=self.sp_oauth)
        playlists = sp.current_user_playlists()
        
        playlist_data = []
        for playlist in playlists['items']:
            playlist_data.append({
                'name': playlist['name'],
                'id': playlist['id']
            })
        
        return jsonify(playlist_data)
    
    def callback(self):
        """Handle the callback from Spotify OAuth."""
        code = request.args.get('code')
        self.sp_oauth.get_access_token(code, as_dict=False)
        return redirect(url_for('dashboard'))
    
    def dashboard(self):
        """Render the dashboard page."""
        token_info = self.cache_handler.get_cached_token()
        if not token_info:
            return redirect(url_for('home'))
        
        sp = Spotify(auth_manager=self.sp_oauth)
        playlists = sp.current_user_playlists()
        
        return render_template('dashboard.html', 
                              playlists=playlists['items'])
    
    def liked_tracks_data(self):
        """Return user's liked tracks as JSON."""
        token_info = self.cache_handler.get_cached_token()
        if not token_info:
            return redirect(url_for('home'))
        
        sp = Spotify(auth_manager=self.sp_oauth)
        results = sp.current_user_saved_tracks(limit=20)
        
        tracks_data = []
        for item in results['items']:
            track = item['track']
            tracks_data.append({
                'name': track['name'],
                'artists': ', '.join(artist['name'] for artist in track['artists']),
                'id': track['id']
            })
        
        return jsonify(tracks_data)
    
    def recommend(self, playlist_id, option='playlist'):
        """
        Flask route that calls the recommend() function with the playlist id
        and returns the recommendations as JSON.
        """
        token_info = self.cache_handler.get_cached_token()
        
        if not token_info:
            return redirect(url_for('authorize'))
            
        if not self.sp_oauth.validate_token(token_info):
            return redirect(url_for('authorize'))
        
        audio_processor = AudioProcessor()
        try:
            recommendations = audio_processor.recommend(playlist_id, self.sp, token_info, option='playlist')
            return jsonify(recommendations)
        except Exception as e:
            return jsonify({"error": f"Error processing recommendations: {str(e)}"})
    
    def recommend_by_recent_songs(self, playlist_id='1', option='liked'):

        token_info = self.cache_handler.get_cached_token()
        
        if not token_info:
            return redirect(url_for('authorize'))
            
        if not self.sp_oauth.validate_token(token_info):
            return redirect(url_for('authorize'))
        
        audio_processor = AudioProcessor()
        try:
            recommendations = audio_processor.recommend(playlist_id, self.sp, token_info, option='liked')
            return jsonify(recommendations)
        except Exception as e:
            return jsonify({"error": f"Error processing recommendations: {str(e)}"})
            
    def run(self, debug=True):
        """Run the Flask application."""
        self.app.run(debug=debug)


if __name__ == '__main__':
    spotify_app = SpotifyFlaskApp()
    spotify_app.run(debug=True)