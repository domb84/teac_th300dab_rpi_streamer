import configparser
import os
from time import sleep

import requests
from blinker import signal


# useful info
# https://github.com/librespot-org/librespot/issues/185
# https://stmorse.github.io/journal/spotify-api.html

class spotify():

    def __init__(self, path, client_id, client_secret):
        # init signal sender
        self.track_data = signal('track-data')

        try:
            self.config = configparser.ConfigParser()
            self.path = path
            # import creds
            self.SPOTIPY_CLIENT_ID = client_id
            self.SPOTIPY_CLIENT_SECRET = client_secret
            self.access_token = None

            if os.path.exists(path):
                print('%s exists' % path)
            else:
                print('%s does not exist' % path)
        except Exception as e:
            print(e)

    def auth_token(self):
        # check if token is valid and refresh if necessary
        try:
            # check if token is valid
            BASE_URL = 'https://api.spotify.com/v1/'
            params = {}
            headers = {
                'Authorization': 'Bearer {token}'.format(token=self.access_token)
            }

            r = requests.get(BASE_URL + 'me/', params=params, headers=headers)
            r = r.json()

            try:
                status = r['error']['status']
                message = r['error']['message']

            except:
                status = r['status']
                message = r['message']

            print("Token status and message: %s %s" % (status, message))

            if status == 401 and 'invalid' in message.lower():
                # refresh token
                AUTH_URL = 'https://accounts.spotify.com/api/token'

                # post
                auth_response = requests.post(AUTH_URL, {
                    'grant_type': 'client_credentials',
                    'client_id': self.SPOTIPY_CLIENT_ID,
                    'client_secret': self.SPOTIPY_CLIENT_SECRET,
                })

                # convert the response to JSON
                auth_response_data = auth_response.json()
                print(auth_response_data)

                # save the access token
                self.access_token = auth_response_data['access_token']

                print("Token refreshed")

            return True

        except Exception as e:
            print(e)
            return False

    def track_metadata(self, track_id):
        token = self.auth_token()
        print("Track id is: %s" % track_id)
        print("Token is: %s" % str(token))

        if token is not False:

            BASE_URL = 'https://api.spotify.com/v1/'
            params = {'ids': track_id}
            headers = {
                'Authorization': 'Bearer {token}'.format(token=self.access_token)
            }

            r = requests.get(BASE_URL + 'tracks/', params=params, headers=headers)
            r = r.json()
            print(r)

            try:
                artist = r['tracks'][0]['artists'][0]['name']
                track_name = r['tracks'][0]['name']
                print(artist, track_name)
                return {'status': 'playing', 'error': '', 'artist': artist, 'track': track_name}
            except Exception as e:
                return {'status': 'error', 'error': e, 'artist': '', 'track': ''}
        else:
            return {'status': 'error', 'error': 'Cannot retrieve track information', 'artist': '', 'track': ''}

    def refresh(self):
        # read the spotify track info from the file
        try:
            self.config.read(self.path)
            self.track_info = self.config
        except:
            pass

    def listener(self):
        # refresh spotify track id
        self.refresh()

        # refresh track info
        try:
            track_id = self.track_info['INFO']['ID']
            event = self.track_info['INFO']['EVENT']
            # self.auth_token()
            track_metadata = self.track_metadata(track_id)
            print(track_metadata)

        # set to none if it can't be retrieved
        except:
            track_id = None

        while True:
            # refresh spotify track id
            self.refresh()

            # refresh track info
            try:
                new_track_id = self.track_info['INFO']['ID']
            # set to none if it can't be retrieved
            except:
                new_track_id = None

            if track_id != new_track_id:
                track_id = new_track_id

                # get track metadata
                track_metadata = self.track_metadata(track_id)

                # send data to signal
                self.track_data.send('spotify', status=track_metadata['status'], error=track_metadata['error'],
                                     artist=track_metadata['artist'], title=track_metadata['track'])
            sleep(1)