import logging
import boto3
import botocore
import base64
import random
import re

from pajbot.models.command import Command
from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


neuralVoices = [
    "Amy",
    "Brian",
    "Camila",
    "Emma",
    "Ivy",
    "Joanna",
    "Joey",
    "Justin",
    "Kendra",
    "Kimberly",
    "Lupe",
    "Matthew",
    "Salli",
]
normalVoices = [
    "Aditi",
    "Astrid",
    "Bianca",
    "Carla",
    "Celine",
    "Chantal",
    "Conchita",
    "Cristiano",
    "Enrique",
    "Filiz",
    "Geraint",
    "Giorgio",
    "Hans",
    "Ines",
    "Jacek",
    "Lea",
    "Liv",
    "Lotte",
    "Lucia",
    "Mads",
    "Marlene",
    "Mathieu",
    "Maxim",
    "Mia",
    "Miguel",
    "Mizuki",
    "Naja",
    "Nicole",
    "Penelope",
    "Raveena",
    "Ricardo",
    "Ruben",
    "Russell",
    "Seoyeon",
    "Takumi",
    "Tatyana",
    "Vicki",
    "Vitoria",
    "Zeina",
    "Zhiyu",
]
allVoices = neuralVoices + normalVoices
voiceSearch = re.compile(r"^\w*:")


class RewardTTSModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Reward TTS"
    DESCRIPTION = "Play text-to-speech based off highlighted messages"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="tts_voice",
            label="Text-to-speech voice",
            type="options",
            required=True,
            default="Nicole",
            options=normalVoices,
        ),
        ModuleSetting(key="random_voice", label="Use random voice", type="boolean", required=True, default=False,),
        ModuleSetting(
            key="plebs_allowed", label="Are plebs allowed to use it?", type="boolean", required=True, default=False,
        ),
        ModuleSetting(
            key="redeemed_id",
            label="ID of redemeed prize",
            type="text",
            required=True,
            default="",
            constraints={"min_str_len": 36, "max_str_len": 36},
        ),
    ]

    def command_skip(self, bot, **rest):
        bot.websocket_manager.emit("skip_highlight")

    def generateTTS(self, username, message):
        if self.bot.is_bad_message(message):
            # Yikes
            self.bot.whisper_login("ales_", f"User {username} tried to do TTS for a banned message: {message}")
            self.bot.whisper_login("datguy1", f"User {username} tried to do TTS for a banned message: {message}")
            return

        voiceResult = voiceSearch.search(message)
        if voiceResult is not None:
            ttsVoice = voiceResult.group()[:-1]
            message = message[len(ttsVoice) + 1 :]
        else:
            ttsVoice = random.choice(allVoices) if self.settings["random_voice"] else self.settings["tts_voice"]

        if ttsVoice not in allVoices:
            ttsVoice = "Joanne"
            self.bot.whisper_login(username, f"Voice {ttsVoice} was not recognised, falling back to Joanne")

        synthArgs = {
            "Engine": "neural" if ttsVoice in neuralVoices else "standard",
            "OutputFormat": "mp3",
            "Text": f"<speak>{message}</speak>",
            "TextType": "ssml",
            "VoiceId": ttsVoice,
            "LexiconNames": ["twitchLex"],
        }

        message = re.sub(r"<.*?>", "", message)
        try:
            synthResp = self.pollyClient.synthesize_speech(**synthArgs)
        except botocore.exceptions.ClientError as e:
            # Some limitation, eg "This voice does not support one of the used SSML features"
            log.exception(f"Error when trying to generate TTS: {e}")
            synthArgs["Text"] = message
            synthArgs["TextType"] = "text"
            synthResp = self.pollyClient.synthesize_speech(**synthArgs)
        except botocore.errorfactory.InvalidSsmlException as e:
            self.bot.whisper_login(username, "Your message syntax is malformed. Falling back to normal.")
            synthArgs["Text"] = message
            synthArgs["TextType"] = "text"
            synthResp = self.pollyClient.synthesize_speech(**synthArgs)

        payload = {
            "speech": base64.b64encode(synthResp["AudioStream"].read()).decode("utf-8"),
            "voice": ttsVoice,
            "user": username,
            "message": message,
        }
        self.bot.websocket_manager.emit("highlight", payload)

    def isHighlightedMessage(self, event):
        for eventTag in event.tags:
            if eventTag["value"] == "highlighted-message":
                return True

        return False

    def on_message(self, source, message, event, **rest):
        if not self.isHighlightedMessage(event) or (self.settings["plebs_allowed"] is False and not source.subscriber):
            return

        self.generateTTS(source.name, message)

    def on_redeem(self, redeemer, redeemed_id, user_input):
        if user_input is not None and redeemed_id == self.settings["redeemed_id"]:
            self.generateTTS(redeemer.name, user_input)

    def load_commands(self, **options):
        self.commands["skiptts"] = Command.raw_command(
            self.command_skip, level=1000, description="Skip currently playing reward TTS"
        )

    def enable(self, bot):
        if not bot:
            return

        self.pollyClient = boto3.Session().client("polly")
        if self.settings["redeemed_id"]:
            HandlerManager.add_handler("on_redeem", self.on_redeem)
        else:
            HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        if not bot:
            return

        if self.settings["redeemed_id"]:
            HandlerManager.remove_handler("on_redeem", self.on_redeem)
        else:
            HandlerManager.remove_handler("on_message", self.on_message)
