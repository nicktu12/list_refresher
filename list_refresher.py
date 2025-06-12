#!/usr/bin/env python3
import sys
import os
import re
import argparse
from typing import List, Dict, Any
import spotipy
from spotipy.oauth2 import SpotifyOAuth

class SpotifyPlaylistRefresher:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """Initialize the Spotify client with OAuth."""
        self.scope = "playlist-modify-public playlist-modify-private playlist-read-private"
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=self.scope
        ))
    
    def extract_playlist_id(self, playlist_url: str) -> str:
        """Extract playlist ID from Spotify URL."""
        # Handle different Spotify URL formats
        patterns = [
            r'spotify:playlist:([a-zA-Z0-9]+)',
            r'open\.spotify\.com/playlist/([a-zA-Z0-9]+)',
            r'spotify\.com/playlist/([a-zA-Z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, playlist_url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract playlist ID from URL: {playlist_url}")
    
    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get all tracks from a playlist."""
        tracks = []
        results = self.sp.playlist_tracks(playlist_id)
        
        while results:
            for item in results['items']:
                if item['track'] and item['track']['id']:  # Skip local files
                    tracks.append({
                        'id': item['track']['id'],
                        'uri': item['track']['uri'],
                        'name': item['track']['name'],
                        'artists': [artist['name'] for artist in item['track']['artists']]
                    })
            
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        
        return tracks
    
    def refresh_playlist(self, playlist_url: str) -> bool:
        """Refresh a playlist by re-adding all tracks."""
        try:
            # Extract playlist ID
            playlist_id = self.extract_playlist_id(playlist_url)
            print(f"Working with playlist ID: {playlist_id}")
            
            # Get playlist info
            playlist_info = self.sp.playlist(playlist_id)
            print(f"Playlist: '{playlist_info['name']}' by {playlist_info['owner']['display_name']}")
            
            # Get all tracks
            tracks = self.get_playlist_tracks(playlist_id)
            if not tracks:
                print("No tracks found in playlist.")
                return False
            
            print(f"Found {len(tracks)} tracks to refresh")
            
            # Get track URIs for batch operations
            track_uris = [track['uri'] for track in tracks]
            
            # Remove all tracks from playlist
            print("Removing all tracks from playlist...")
            # Spotify API has a limit of 100 tracks per request
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i:i+100]
                self.sp.playlist_remove_all_occurrences_of_items(playlist_id, batch)
            
            # Re-add all tracks to playlist
            print("Re-adding all tracks to playlist...")
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i:i+100]
                self.sp.playlist_add_items(playlist_id, batch)
            
            print(f"✅ Successfully refreshed playlist '{playlist_info['name']}'!")
            return True
            
        except Exception as e:
            print(f"❌ Error refreshing playlist: {str(e)}")
            return False

def get_credentials():
    """Get Spotify credentials from environment variables."""
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
    
    missing_vars = []
    if not client_id:
        missing_vars.append('SPOTIFY_CLIENT_ID')
    if not client_secret:
        missing_vars.append('SPOTIFY_CLIENT_SECRET')
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables:")
        print("export SPOTIFY_CLIENT_ID='your_client_id'")
        print("export SPOTIFY_CLIENT_SECRET='your_client_secret'")
        print("export SPOTIFY_REDIRECT_URI='your_redirect_uri'  # Optional, defaults to http://localhost:8888/callback")
        sys.exit(1)
    
    return client_id, client_secret, redirect_uri

def main():
    parser = argparse.ArgumentParser(description='Refresh a Spotify playlist by re-adding all tracks')
    parser.add_argument('playlist_url', help='Spotify playlist URL')
    
    args = parser.parse_args()
    
    # Get credentials from environment variables
    client_id, client_secret, redirect_uri = get_credentials()
    
    print(f"Using redirect URI: {redirect_uri}")
    
    # Initialize the refresher
    refresher = SpotifyPlaylistRefresher(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )
    
    # Refresh the playlist
    success = refresher.refresh_playlist(args.playlist_url)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
