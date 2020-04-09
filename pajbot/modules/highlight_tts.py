import logging
import requests

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class HighlightTTSModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Highlight TTS"
    DESCRIPTION = "Play text-to-speech based off highlighted messages"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="tts_voice",
            label="Text-to-speech voice",
            type="text",
            required=True,
            placeholder="",
            default="Nicole",
            constraints={"min_str_len": 3, "max_str_len": 30},
        ),
    ]

    def isHighlightedMessage(self, event):
        for eventTag in event.tags:
            if eventTag['value'] == 'highlighted-message':
                return True

        return False

    def on_message(self, source, message, event, **rest):
        if not self.isHighlightedMessage(event):
            return

        if self.bot.is_bad_message(message) or not source.subscriber:
            return

        payload = {"text": message, "voice": self.settings["tts_voice"]}
        r = requests.post("https://streamlabs.com/polly/speak", data=payload)
        if r.status_code != 200 or r.json()["success"] is False:
            log.exception(f"Error when trying to generate TTS: {r.json()}")
            return

        payload = {"link": r.json()["speak_url"], "user": source.name, "message": message}
        self.bot.websocket_manager.emit("highlight", payload)

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)