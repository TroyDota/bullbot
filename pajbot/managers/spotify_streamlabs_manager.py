import logging
from pajbot.managers.handler import HandlerManager

log = logging.getLogger("pajbot")


class SpotifyStreamLabsManager:
    def __init__(self, bot):
        self.bot = bot
        self.currentSong = {"title": None, "requested_by": None}
        # Handlers
        HandlerManager.add_handler("resume_spotify", self.play_spotify)
        HandlerManager.add_handler("pause_spotify", self.pause_spotify)
        HandlerManager.add_handler("change_state", self.change_state)
        self.isPaused = False
        self.was_playing = False

    def change_state(self, state):
        self.isPaused = state

    def play_spotify(self):
        if self.was_playing:
            self.currentSong["title"] = None
            self.currentSong["requested_by"] = None
            self.bot.spotify_api.play()

    def pause_spotify(self, title, requested_by):
        isPlaying, name, artists = self.bot.spotify_api.state()
        self.was_playing = isPlaying or self.was_playing
        self.currentSong["title"] = title
        self.currentSong["requested_by"] = requested_by
        self.bot.spotify_api.pause()

    def get_current_song(self):
        return_song_data = {}
        if self.currentSong["title"] is None:
            isPlaying, name, artists = self.bot.spotify_api.state()
            if not isPlaying:
                return return_song_data

            return_song_data["playing"] = True
            return_song_data["spotify"] = True
            return_song_data["title"] = name
            return_song_data["artists"] = artists
            return return_song_data

        return_song_data["playing"] = True
        return_song_data["title"] = self.currentSong["title"]
        return_song_data["requested_by"] = self.currentSong["requested_by"]
        return return_song_data
