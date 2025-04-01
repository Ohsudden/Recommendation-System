import spotipy
import spotipy.util as util
import pandas as pd
import os
import yt_dlp
import librosa
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from sklearn.preprocessing import StandardScaler

def songs_from_playlist(playlist_name, id_dic, client_id, client_secret):
    token = spotipy.util.prompt_for_user_token('user-library-read', client_id= client_id, client_secret=client_secret, redirect_uri='http://localhost:5000/callback')
    sp_object = spotipy.Spotify(auth=token)
    items = sp_object.playlist(id_dic[playlist_name])['tracks']['items']
    data = [
        {
            'artist': item['track']['artists'][0]['name'],
            'name': item['track']['name'],
            'id': item['track']['id'],
            'url': f"https://open.spotify.com/track/{item['track']['id']}",  
            'date_added': pd.to_datetime(item['added_at'])
        }
        for item in items
    ]
    playlist = pd.DataFrame(data)
    return playlist



def search_and_download(track_name, artist, output_path='downloads'):
    query = f"{track_name} {artist} official audio"
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    os.makedirs(output_path, exist_ok=True)
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

def extract_audio_features(audio_file, sr=22050):
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

def process_track(row, output_path='downloads'):
    track_name = row['name_tracks']
    artist = row['name_artist']
    print(f"Processing: {track_name} by {artist}")
    
    try:
        audio_file = search_and_download(track_name, artist, output_path=output_path)
        print(f"Downloaded: {audio_file}")

        features = extract_audio_features(audio_file)
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

def process_tracks(df, output_path='downloads'):
    features_list = []

    with ThreadPoolExecutor(max_workers=4) as download_executor:
        download_futures = {download_executor.submit(search_and_download, row['name_tracks'], row['name_artist'], output_path): row for idx, row in df.iterrows()}
        extraction_tasks = []
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
        extract_futures = {extract_executor.submit(extract_audio_features, row['audio_file']): row for row in extraction_tasks}
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

def normalize(df, columns):
    scaler = StandardScaler()
    df[columns] = scaler.fit_transform(df[columns])
    return df