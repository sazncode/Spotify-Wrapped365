import os
from keep_alive import keep_alive
from keep_alive import keep_alive
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time
import datetime
import gspread
from dotenv import load_dotenv
import logging
import json

GSscope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
# Update with your own JSON Enviornment Variable
my_secret = json.loads(os.environ['GSPREAD_KEYS'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(my_secret, GSscope)
gc = gspread.authorize(creds)
sh = gc.open('Wrapped365')

# Update with your own Spotify Credentials (Client ID, Secret Client ID, redirect, and username)

SPOTIPY_CLIENT = os.environ['client_sec']
SPOTIPY_SECRET_CLIENT = os.environ['sec_id']
SPOTIPY_REDIRECT = os.environ['redirec']
SCOPE = "user-top-read playlist-modify-private playlist-modify-public user-library-modify user-library-read playlist-read-private"
USERNAME = 'frostscope'

# Authorize
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT, client_secret=SPOTIPY_SECRET_CLIENT, redirect_uri=SPOTIPY_REDIRECT, scope=SCOPE, username=USERNAME, open_browser=False))

def get_top_artists(time_period):
    top_artists = sp.current_user_top_artists(time_range=time_period)
    artist_info = []
    for artist in top_artists['items']:
        artist_info.append([artist['name'], artist['external_urls']
                           ['spotify'], artist['images'][0]['url']])
    return artist_info

def get_track_ids(time_frame):
    track_ids = []
    for song in time_frame['items']:
        track_ids.append(song['id'])
    return track_ids

def get_track_features(id):
    meta = sp.track(id)
    # meta
    name = meta['name']
    album = meta['album']['name']
    artist = meta['album']['artists'][0]['name']
    spotify_url = meta['external_urls']['spotify']
    album_cover = meta['album']['images'][0]['url']
    track_info = [name, album, artist, spotify_url, album_cover]
    return track_info

# insert into sheet
def insert_to_gsheet(track_ids, time_period):
    # loop over track ids
    tracks = []
    for i in range(len(track_ids)):
        track = get_track_features(track_ids[i])
        tracks.append(track)
    # create dataframe

    df = pd.DataFrame(
        tracks, columns=['name', 'album', 'artist', 'spotify_url', 'album_cover'])
    worksheet = sh.worksheet(f'{time_period}')
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    print(time_period + ' Tracks Done.')
    return tracks
def insert_artists_to_gsheet(artist_info, time_period):
    df = pd.DataFrame(artist_info, columns=[
                      'name', 'spotify_url', 'artist_cover'])
    worksheet = sh.worksheet(f'{time_period} Artists')
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    print(time_period + ' Artist Done.')
    return artist_info

def Wrapped():
  waitSecs = 21600
  playlistExists = False
  time_ranges = ['short_term', 'medium_term', 'long_term']
  for time_period in time_ranges:
    top_tracks = sp.current_user_top_tracks(
        limit=50, offset=0, time_range=time_period)
    track_ids = get_track_ids(top_tracks)
    insert_to_gsheet(track_ids, time_period)
    top_artists = get_top_artists(time_period)
    insert_artists_to_gsheet(top_artists, time_period)

    # get list of user's playlists
    playlists = sp.current_user_playlists()
    # check if a user has a playlist called short term
    for playlist in playlists['items']:
        if playlist['name'] == time_period:
            playlist_id = playlist['id']
            #remove all songs in playlist
            sp.user_playlist_replace_tracks(USERNAME, playlist_id, track_ids)
            playlistExists = True
            break
    if playlistExists == False:
        playlist_id = sp.user_playlist_create(USERNAME, f'{time_period}', public=True, collaborative=False,
                        description=f'Top Played Tracks for {time_period}. Generated using Prem\'s Wrapped365 Python Project. Updated every {waitSecs} seconds if there is a new track placement.')['id']
        sp.user_playlist_add_tracks(USERNAME, playlist_id, track_ids)
    playlistExists = False

# Run script to insert into sheet
keep_alive()

while True:
  Wrapped()
  time.sleep(21600)
