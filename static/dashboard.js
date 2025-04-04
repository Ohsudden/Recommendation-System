function getRecommendations(playlistId) {
    document.getElementById('playlists-container').style.display = 'none';
    document.getElementById('recommendations-container').style.display = 'block';
    document.getElementById('recommendations-list').innerHTML = '<p>Loading recommendations...</p>';
    
    fetch(`/recommend/${playlistId}`)
        .then(response => response.json())
        .then(recommendations => {
            console.log("Recommendations:", recommendations);
            const recommendationsList = document.getElementById('recommendations-list');
            recommendationsList.innerHTML = '';
            if (recommendations.error) {
                recommendationsList.innerHTML = `<p>Error: ${recommendations.error}</p>`;
                return;
            }
            if (Array.isArray(recommendations) && recommendations.length > 0) {
                recommendations.forEach(rec => {
                    const trackId = rec.track_id;
                    const similarity = rec.similarity;
                    const recItem = document.createElement('div');
                    recItem.className = 'recommendation-item';
                    recItem.innerHTML = `
                        <p>Similarity score: ${(similarity * 100).toFixed(2)}%</p>
                        <iframe 
                            style="border-radius:12px" 
                            src="https://open.spotify.com/embed/track/${trackId}?utm_source=generator" 
                            width="100%" 
                            height="152" 
                            frameBorder="0" 
                            allowfullscreen="" 
                            allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" 
                            loading="lazy">
                        </iframe>
                    `;
                    recommendationsList.appendChild(recItem);
                });
            } else {
                recommendationsList.innerHTML = '<p>No recommendations found.</p>';
            }
        })
        .catch(error => {
            console.error("Error fetching recommendations:", error);
            document.getElementById('recommendations-list').innerHTML = `<p>Error loading recommendations: ${error.message}</p>`;
        });
}

function getLikedRecommendations() {
    document.getElementById('liked-songs-container').style.display = 'none';
    document.getElementById('recommendations-container').style.display = 'block';
    document.getElementById('recommendations-list').innerHTML = '<p>Loading recommendations...</p>';

    fetch(`/recommend-by-recent-songs/`)
        .then(response => response.json())
        .then(recommendations => {
            console.log("Liked Recommendations:", recommendations);
            const recommendationsList = document.getElementById('recommendations-list');
            recommendationsList.innerHTML = '';
            if (recommendations.error) {
                recommendationsList.innerHTML = `<p>Error: ${recommendations.error}</p>`;
                return;
            }
            if (Array.isArray(recommendations) && recommendations.length > 0) {
                recommendations.forEach(rec => {
                    const trackId = rec.track_id;
                    const similarity = rec.similarity;
                    const recItem = document.createElement('div');
                    recItem.className = 'recommendation-item';
                    recItem.innerHTML = `
                        <p>Similarity score: ${(similarity * 100).toFixed(2)}%</p>
                        <iframe 
                            style="border-radius:12px" 
                            src="https://open.spotify.com/embed/track/${trackId}?utm_source=generator" 
                            width="100%" 
                            height="152" 
                            frameBorder="0" 
                            allowfullscreen="" 
                            allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" 
                            loading="lazy">
                        </iframe>
                    `;
                    recommendationsList.appendChild(recItem);
                });
            } else {
                recommendationsList.innerHTML = '<p>No recommendations found.</p>';
            }
        })
        .catch(error => {
            console.error("Error fetching liked recommendations:", error);
            document.getElementById('recommendations-list').innerHTML = `<p>Error loading recommendations: ${error.message}</p>`;
        });
}

document.getElementById('show-playlists').addEventListener('click', function() {
    document.getElementById('main-options').style.display = 'none';
    document.getElementById('playlists-container').style.display = 'block';

    fetch('/playlists-data')
        .then(response => response.json())
        .then(playlists => {
            const playlistsList = document.getElementById('playlists-list');
            playlistsList.innerHTML = '';

            playlists.forEach(playlist => {
                const playlistItem = document.createElement('div');
                playlistItem.className = 'playlist-item';
                playlistItem.innerHTML = `
                    <div>${playlist.name}</div>
                    <button class="btn" onclick="getRecommendations('${playlist.id}')">
                        Get Recommendations
                    </button>
                `;
                playlistsList.appendChild(playlistItem);
            });
        })
        .catch(error => {
            document.getElementById('playlists-list').innerHTML = `<p>Error loading playlists: ${error.message}</p>`;
        });
});

document.getElementById('show-liked-songs').addEventListener('click', function() {
    document.getElementById('main-options').style.display = 'none';
    document.getElementById('liked-songs-container').style.display = 'block';
    
    fetch('/liked-tracks-data')
        .then(response => response.json())
        .then(tracks => {
            const likedSongsList = document.getElementById('liked-songs-list');
            likedSongsList.innerHTML = '';
            
            tracks.forEach(track => {
                const trackItem = document.createElement('div');
                trackItem.className = 'playlist-item';
                trackItem.innerHTML = `
                    <div>${track.name}</div>
                    <div><small>by ${track.artists}</small></div>
                `;
                likedSongsList.appendChild(trackItem);
            });
        })
        .catch(error => {
            document.getElementById('liked-songs-list').innerHTML = `<p>Error loading liked songs: ${error.message}</p>`;
        });
});
function getTopTracks() {
    fetch('/top-tracks')
        .then(response => response.json())
        .then(data => {
            const tracks = data.items;
            const topTracksList = document.getElementById('top-tracks-list');
            topTracksList.innerHTML = '';
            
            if (Array.isArray(tracks)) {
                tracks.forEach(track => {
                    const trackItem = document.createElement('div');
                    trackItem.className = 'music-item';
                    const imageUrl = (track.album && track.album.images && track.album.images.length > 0)
                                     ? track.album.images[0].url
                                     : 'https://via.placeholder.com/150';
                    trackItem.innerHTML = `
                        <div class="cover" style="background-image: url('${imageUrl}');"></div>
                        <div class="track-info">
                            <div class="track-name">${track.name}</div>
                            <div class="track-artist"><small>by ${track.artists.map(artist => artist.name).join(', ')}</small></div>
                        </div>
                    `;
                    topTracksList.appendChild(trackItem);
                });
            } else {
                topTracksList.innerHTML = '<p>No top tracks found.</p>';
            }
        })
        .catch(error => {
            document.getElementById('top-tracks-list').innerHTML = `<p>Error loading top tracks: ${error.message}</p>`;
        });
}

document.addEventListener("DOMContentLoaded", function() {
    getTopTracks();
});
document.getElementById('get-liked-recommendations').addEventListener('click', function() {
    getLikedRecommendations();
});

document.getElementById('back-from-playlists').addEventListener('click', function() {
    document.getElementById('playlists-container').style.display = 'none';
    document.getElementById('main-options').style.display = 'flex';
});

document.getElementById('back-from-liked-songs').addEventListener('click', function() {
    document.getElementById('liked-songs-container').style.display = 'none';
    document.getElementById('main-options').style.display = 'flex';
});

document.getElementById('back-from-recommendations').addEventListener('click', function() {
    document.getElementById('recommendations-container').style.display = 'none';
    document.getElementById('main-options').style.display = 'flex';
});