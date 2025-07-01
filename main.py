import os
from flask import Flask, session, redirect, url_for, request, render_template, jsonify
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from analysis_function import AudioProcessor
from datetime import timedelta
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import re

load_dotenv()


class SpotifyFlaskApp:
    def __init__(self):
        self.app = Flask(__name__, template_folder='C:/Users/vova2/PycharmProjects/SpotifyMusic')
        self.app.config['SECRET_KEY'] = os.urandom(64)
        self.app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
        self.app.config['SESSION_PERMANENT'] = True
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
        self.scope = 'user-library-read user-top-read'

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

    def chat_api(self):
        user_message = request.json.get("message")
        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=500,
            timeout=None,
            max_retries=2,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a helpful assistant for a Spotify music recommendation web app. "
             "Answer ONLY about features available in this app. "
             "The user can: view their top tracks, top artists, top genres, playlists, liked songs, "
             "and get recommendations based on their playlists or liked songs. "
             "If the user asks how to get recommendations, explain how to use the app's buttons and features. "
             "Do NOT give generic internet advice or mention other services."),
            ("user", "{input}")
        ])
        chain = prompt | llm

        response = chain.invoke({"input": user_message})
        clean_text = re.sub(r'(\*\*|__|\*|`)', '', response.content)
        return jsonify({"response": clean_text})

    def register_routes(self):
        self.app.route('/', endpoint='home')(self.home)
        self.app.route('/authorization', endpoint='authorize')(self.authorize)
        self.app.route('/playlists-data', endpoint='playlists_data')(self.playlists_data)
        self.app.route('/callback', endpoint='callback')(self.callback)
        self.app.route('/dashboard', endpoint='dashboard')(self.dashboard)
        self.app.route('/liked-tracks-data', endpoint='liked_tracks_data')(self.liked_tracks_data)
        self.app.route('/recommend/<playlist_id>', endpoint='recommend')(self.recommend)
        self.app.route('/recommend-by-recent-songs/', endpoint='recommend_by_recent_songs')(
            self.recommend_by_recent_songs)
        self.app.route('/top-tracks', endpoint='top_tracks')(self.top_tracks)
        self.app.route('/top-artists', endpoint='top_artists')(self.get_top_artists)
        self.app.route('/top-genres', endpoint='top_genres')(self.get_top_genres)
        self.app.add_url_rule('/chat-api', view_func=self.chat_api, methods=['POST'])

    def home(self):
        return render_template('index.html')

    def authorize(self):
        token_info = self.cache_handler.get_cached_token()
        if not self.sp_oauth.validate_token(token_info):
            auth_url = self.sp_oauth.get_authorize_url()
            return redirect(auth_url)
        else:
            return redirect(url_for('dashboard'))

    def playlists_data(self):
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
        code = request.args.get('code')
        self.sp_oauth.get_access_token(code, as_dict=False)
        return redirect(url_for('dashboard'))

    def dashboard(self):
        token_info = self.cache_handler.get_cached_token()
        if not token_info:
            return redirect(url_for('home'))

        sp = Spotify(auth_manager=self.sp_oauth)
        playlists = sp.current_user_playlists()

        return render_template('dashboard.html',
                               playlists=playlists['items'])

    def liked_tracks_data(self):
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

    def top_tracks(self):
        token_info = self.cache_handler.get_cached_token()
        if not token_info or not self.sp_oauth.validate_token(token_info):
            return jsonify({"error": "Not authorized"}), 401

        current_user_top_tracks = self.sp.current_user_top_tracks(limit=3, time_range='medium_term')
        return jsonify(current_user_top_tracks)

    def get_top_artists(self):
        token_info = self.cache_handler.get_cached_token()
        if not token_info or not self.sp_oauth.validate_token(token_info):
            return jsonify({"error": "Not authorized"}), 401

        current_user_top_artists = self.sp.current_user_top_artists(limit=3, time_range='medium_term')
        return jsonify(current_user_top_artists)

    def get_top_genres(self):
        token_info = self.cache_handler.get_cached_token()
        if not token_info or not self.sp_oauth.validate_token(token_info):
            return jsonify({"error": "Not authorized"}), 401

        current_user_top_genres = self.sp.current_user_top_artists(limit=50, time_range='medium_term')
        genres = [genre for artist in current_user_top_genres['items'] for genre in artist.get('genres', [])]

        genre_freq = {}
        for genre in genres:
            genre_freq[genre] = genre_freq.get(genre, 0) + 1

        sorted_genres = sorted(genre_freq.items(), key=lambda x: x[1], reverse=True)
        filtered_genres = [item for item in sorted_genres if item[1] > 1]
        top_5_with_counts = filtered_genres[:5]
        top_5_genres = [genre for genre, count in top_5_with_counts]

        return jsonify(top_5_genres)

    def run(self, debug=True):
        self.app.run(debug=debug)


if __name__ == '__main__':
    spotify_app = SpotifyFlaskApp()
    spotify_app.run(debug=True)
