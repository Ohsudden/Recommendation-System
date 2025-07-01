import os
import re
import yt_dlp
import librosa
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import spotipy
import spotipy.util as util
from sklearn.metrics.pairwise import cosine_similarity

class AudioProcessor:
    def __init__(self, output_path='downloads'):
        self.output_path = output_path
        os.makedirs(self.output_path, exist_ok=True)
    
    def search_and_download(self, track_name, artist):

        query = f"{track_name} {artist} official audio"
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'outtmpl': f'{self.output_path}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        search_url = f"ytsearch1:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=True)
            if 'entries' in info and info['entries']:
                video = info['entries'][0]
                filename = ydl.prepare_filename(video)
                base, _ = os.path.splitext(filename)
                audio_file = base + ".mp3"
                return audio_file
            else:
                raise Exception("No search results found.")

    def extract_audio_features(self, audio_file, sr=22050):

        y, sr = librosa.load(audio_file, sr=sr)
        stft = np.abs(librosa.stft(y))
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        features = {
            'stft': stft,
            'spectral_centroid': spectral_centroid,
            'zero_crossing_rate': zero_crossing_rate,
            'mfccs': mfccs
        }
        return features

    def process_track(self, row):

        track_name = row['name_tracks']
        artist = row['name_artist']
        print(f"Processing: {track_name} by {artist}")
        try:
            audio_file = self.search_and_download(track_name, artist)
            print(f"Downloaded: {audio_file}")
            features = self.extract_audio_features(audio_file)
            features['track_id'] = row['id_tracks']
            if os.path.exists(audio_file):
                os.remove(audio_file)
                print(f"Deleted: {audio_file}")
            else:
                print(f"File not found for deletion: {audio_file}")
            return features
        except Exception as e:
            print(f"Error processing {track_name} by {artist}: {e}")
            return None

    def process_tracks(self, df):

        features_list = []
        extraction_tasks = []

        with ThreadPoolExecutor(max_workers=4) as download_executor:
            download_futures = {download_executor.submit(self.search_and_download, row['name_tracks'], row['name_artist']): row 
                                for idx, row in df.iterrows()}
            for future in download_futures:
                row = download_futures[future]
                try:
                    audio_file = future.result()
                    row['audio_file'] = audio_file
                    print(f"Downloaded: {audio_file}")
                    extraction_tasks.append(row)
                except Exception as e:
                    print(f"Error downloading {row['name_tracks']} by {row['name_artist']}: {e}")

        with ProcessPoolExecutor(max_workers=4) as extract_executor:
            extract_futures = {extract_executor.submit(self.extract_audio_features, row['audio_file']): row 
                                for row in extraction_tasks}
            for future in extract_futures:
                row = extract_futures[future]
                try:
                    features = future.result()
                    features['track_id'] = row['id_tracks']
                    features_list.append(features)
                    audio_file = row['audio_file']
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                        print(f"Deleted: {audio_file}")
                    else:
                        print(f"File not found for deletion: {audio_file}")
                except Exception as e:
                    print(f"Error processing {row['name_tracks']} by {row['name_artist']}: {e}")

        return features_list

    def recommend(self, playlist_id, sp, token_info, option):
        if not token_info:
            return {"error": "User not authenticated"}
        
        if option == "liked":
            try:
                results = sp.current_user_saved_tracks(limit=20)
            except Exception as e:
                print(f"Error fetching liked tracks: {e}")
                return {"error": "Could not fetch liked tracks"}
            
            tracks = []
            for item in results['items']:
                track = item['track']
                if track is None:
                    continue
                tracks.append({
                    'name_tracks': track['name'],
                    'name_artist': track['artists'][0]['name'],
                    'id_tracks': track['id']
                })
        elif option == "playlist":
            try:
                tracks_response = sp.playlist_tracks(playlist_id)
            except Exception as e:
                print(f"Error fetching playlist tracks: {e}")
                return {"error": "Could not fetch playlist tracks"}
            
            tracks = []
            for item in tracks_response['items']:
                track = item['track']
                if track is None:
                    continue
                tracks.append({
                    'name_tracks': track['name'],
                    'name_artist': track['artists'][0]['name'],
                    'id_tracks': track['id']
                })
        else:
            return {"error": "Invalid recommendation option"}
        
        if not tracks:
            return {"error": "No songs found for recommendation"}

        dataset_processor = DatasetProcessor(dataset_path='static/general_dataset.csv')
        try:
            dataset_df = pd.read_csv(dataset_processor.dataset_path)
        except Exception as e:
            print(f"Dataset not found or error reading dataset: {e}")
            dataset_df = pd.DataFrame()
        
        existing_ids = set(dataset_df['track_id'].tolist()) if (not dataset_df.empty and 'track_id' in dataset_df.columns) else set()
        missing_songs = [song for song in tracks if song['id_tracks'] not in existing_ids]
        
        if missing_songs:
            print(f"Processing {len(missing_songs)} missing songs...")
            audio_processor = AudioProcessor()
            missing_df = pd.DataFrame(missing_songs)
            features_list = audio_processor.process_tracks(missing_df)
            features_list = [feat for feat in features_list if feat is not None]
            if features_list:
                features_df = pd.DataFrame(features_list)
                dataset_df = dataset_processor.adding_features_to_set(features_df)
            else:
                print("No features could be extracted for missing songs.")
        
        dataset_df = DatasetProcessor.expand_metric_columns(
            dataset_df,
            metric_cols=['spectral_centroid', 'zero_crossing_rate', 'mfccs']
        )
        
        expanded_cols = [col for col in dataset_df.columns if 
                        col.startswith('spectral_centroid_') or 
                        col.startswith('zero_crossing_rate_') or 
                        col.startswith('mfccs_')]
        
        if not expanded_cols:
            print("No expanded feature columns found.")
            return {"error": "No expanded features available"}
        
        dataset_df = DatasetProcessor.normalize(dataset_df, expanded_cols)
        
        track_ids = [song['id_tracks'] for song in tracks]
        playlist_df = dataset_df[dataset_df['track_id'].isin(track_ids)]
        candidate_df = dataset_df[~dataset_df['track_id'].isin(track_ids)]
        
        if playlist_df.empty:
            print("No valid tracks found in dataset.")
            return {"error": "No feature vectors available"}
        
        if candidate_df.empty:
            print("No new candidate songs available for recommendations.")
            return {"error": "No new candidate songs available"}
        
        playlist_vector = playlist_df[expanded_cols].mean(axis=0).values    
        candidate_vectors = candidate_df[expanded_cols].values
        similarities = cosine_similarity([playlist_vector], candidate_vectors)[0]
        candidate_df['similarity'] = similarities
        
        recommended_df = candidate_df.sort_values(by='similarity', ascending=False).head(10)
        recommended_songs = recommended_df[['track_id', 'similarity']].to_dict(orient='records')
        
        return recommended_songs


class DatasetProcessor:
    def __init__(self, dataset_path='static/general_dataset.csv'):
        self.dataset_path = dataset_path

    def adding_features_to_set(self, df):

        try:
            general_dataset = pd.read_csv(self.dataset_path)
        except Exception as e:
            print(f"Error reading dataset at {self.dataset_path}: {e}")
            general_dataset = pd.DataFrame()
        new_general_dataset = pd.concat([general_dataset, df])
        new_general_dataset = new_general_dataset.drop_duplicates(subset=['track_id'], keep='last')
        new_general_dataset.to_csv(self.dataset_path, index=False)
        return new_general_dataset

    @staticmethod
    def normalize(df, columns):
        for col in columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df[columns] = df[columns].fillna(0)
        scaler = StandardScaler()
        df[columns] = scaler.fit_transform(df[columns])
        return df

    @staticmethod
    def parse_array(value):
        if isinstance(value, (list, np.ndarray)):
            return list(value)
        if isinstance(value, str):  
            cleaned_str = value.replace("\n", " ").strip()
            number_strings = re.findall(r'-?\d+\.?\d*(?:e[+-]?\d+)?', cleaned_str)
            return [float(num) for num in number_strings]
        return []

    @staticmethod
    def expand_metric_columns(df, metric_cols=['stft', 'spectral_centroid', 'zero_crossing_rate', 'mfccs']):

        for col in metric_cols:
            new_col_list = col + '_list'
            df[new_col_list] = df[col].apply(DatasetProcessor.parse_array)
            
            max_len = df[new_col_list].apply(len).max()
            for i in range(max_len):
                new_col_name = f'{col}_{i+1}'
                df[new_col_name] = df[new_col_list].apply(lambda x: x[i] if i < len(x) else np.nan)
            
            df.drop(columns=[new_col_list], inplace=True)
        df = df.drop(columns=metric_cols, axis=1)
        return df
    

