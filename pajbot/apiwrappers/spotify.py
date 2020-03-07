import logging
import base64

from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.authentication.access_token import SpotifyAccessToken

log = logging.getLogger(__name__)


class SpotifyApi(BaseAPI):
    def __init__(self, bot, redis, client_id, client_secret, redirect_uri):
        super().__init__(base_url="https://api.spotify.com/v1/", redis=redis)
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.account_base_url = "https://accounts.spotify.com"
        self.bot = bot
        if self.bot.spotify_token_manager.token is None or self.bot.spotify_token_manager.token.access_token is None:
            log.error("Spotify Token not found")
            return

        self.bearer_auth = {"Authorization": "Bearer " + self.bot.spotify_token_manager.token.access_token}
        self.basic_auth = {"Authorization": "Basic " + str(base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")), "utf-8")}

    def pause(self):
        if not self.bearer_auth:
            return
        self.put(endpoint="me/player/pause", headers=self.bearer_auth)

    def play(self):
        if not self.bearer_auth:
            return
        self.put(endpoint="me/player/play", headers=self.bearer_auth)

    def state(self):
        if not self.bearer_auth:
            return tuple([False, None, None])
        data = self.get(endpoint="me/player", headers=self.bearer_auth)
        if data is None:
            return tuple([False, None, None])
        artists = []

        for artist in data["item"]["artists"]:
            artists.append(artist["name"])

        return tuple([data["is_playing"], data["item"]["name"], artists])

    def get_user_access_token(self, code):
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri}
        response = self.post("/api/token", data=data, headers=self.basic_auth, base_url=self.account_base_url)

        # {
        #       "access_token": "NgCXRK...MzYjw",
        #       "token_type": "Bearer",
        #       "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-email user-read-private",
        #       "expires_in": 3600,
        #       "refresh_token": "NgAagA...Um_SHo"
        # }

        log.info("Recieved token")
        return SpotifyAccessToken.from_api_response(response)

    def refresh_user_access_token(self, refresh_token):
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        response = self.post("/api/token", data=data, headers=self.basic_auth, base_url=self.account_base_url)

        # {
        #       "access_token": "NgA6ZcYI...ixn8bUQ",
        #       "token_type": "Bearer",
        #       "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-email user-read-private",
        #       "expires_in": 3600
        # }

        if "refresh_token" not in response:
            response["refresh_token"] = refresh_token
        log.info("Refreshed spotify token")
        return SpotifyAccessToken.from_api_response(response)
