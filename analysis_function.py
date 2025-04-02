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

class AudioProcessor:
    def __init__(self, output_path='downloads'):
        self.output_path = output_path
        os.makedirs(self.output_path, exist_ok=True)
    
    def search_and_download(self, track_name, artist):
        """
        Downloads the audio for a given track by searching on YouTube.
        """
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
        """
        Extracts various audio features from the audio file.
        """
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
        """
        Processes a single track: downloads the audio, extracts features, and cleans up.
        Expects the row to have keys 'name_tracks', 'name_artist', and 'id_tracks'.
        """
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
        """
        Process a DataFrame of tracks concurrently.
        Expects DataFrame to have columns: 'name_tracks', 'name_artist', 'id_tracks'.
        """
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


class DatasetProcessor:
    def __init__(self, dataset_path='static/general_dataset.csv'):
        self.dataset_path = dataset_path

    def adding_features_to_set(self, df):
        """
        Concatenates a new DataFrame with the existing dataset
        and writes back to the CSV file.
        """
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
        """
        Normalizes the given columns of the DataFrame using StandardScaler.
        """
        scaler = StandardScaler()
        df[columns] = scaler.fit_transform(df[columns])
        return df

    @staticmethod
    def parse_array(array_str):
        """
        Parses a string representation of an array into a list of floats.
        """
        cleaned_str = array_str.replace("\n", " ").strip()
        number_strings = re.findall(r'-?\d+\.?\d*(?:e[+-]?\d+)?', cleaned_str)
        return [float(num) for num in number_strings]

    @staticmethod
    def expand_metric_columns(df, metric_cols=['stft', 'spectral_centroid', 'zero_crossing_rate', 'mfccs']):
        """
        Expands each metric column (which is a string representation of an array)
        into multiple columns and then drops the original metric columns.
        """
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
    

