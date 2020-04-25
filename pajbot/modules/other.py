import random
import string
import logging

from pajbot.models.command import Command
from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class OtherModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Other"
    DESCRIPTION = "Where other shit doesn't fit"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="message_subonly",
            label="Enabling subscribers-only message",
            type="text",
            required=True,
            placeholder="monkaO peepoArriveInJail peepoArriveInJail peepoArriveInJail peepoArriveInJail Caging the plebs",
            default="monkaO peepoArriveInJail peepoArriveInJail peepoArriveInJail peepoArriveInJail Caging the plebs",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_suboff",
            label="Disabling subscribers-only message",
            type="text",
            required=True,
            placeholder="Plebs incoming! peepoHrun",
            default="Plebs incoming! peepoHrun",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(key="enable_drop", label="Enable drop Jebait", type="boolean", required=True, default=True),
        ModuleSetting(
            key="drop_prefix",
            label="Prefix for drop message",
            type="text",
            required=False,
            default="",
            constraints={"min_str_len": 10, "max_str_len": 50},
        ),
    ]

    def __init__(self, bot):
        self.keyCharList = string.ascii_uppercase + string.digits
        super().__init__(bot)

    def generateKey(self, sectionLength=5):
        return "".join(random.choice(self.keyCharList) for i in range(5))

    def viewbots_command(self, bot, message, **rest):
        messageNum = 1
        try:
            messageNum = int(message)
        except (TypeError, ValueError):
            pass

        for i in range(messageNum):
            bot.say(f"VIEWBOT #{random.randint(10000, 99999)} REPORTING IN MrDestructoid 7")

    def drop_command(self, bot, **rest):
        builtString = f"{self.settings['drop_prefix']} " if self.settings["drop_prefix"] is not None else ""
        bot.say(builtString + f"{self.generateKey()}-{self.generateKey()}-{self.generateKey()}")

    def on_pubnotice(self, channel, msg_id, message):
        if msg_id == "subs_on":
            self.bot.me(self.get_phrase("message_subonly"))
        elif msg_id == "subs_off":
            self.bot.me(self.get_phrase("message_suboff"))

    def load_commands(self, **options):
        if self.settings["enable_drop"]:
            self.commands["drop"] = Command.raw_command(
                self.drop_command, delay_all=1, delay_user=15, description="Wow! Get a drop!", cost=0
            )

            self.commands["drops"] = self.commands["drop"]

        self.commands["viewbots"] = Command.raw_command(self.viewbots_command, level=1000)

    def enable(self, bot):
        if not bot:
            return

        HandlerManager.add_handler("on_pubnotice", self.on_pubnotice)

    def disable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        HandlerManager.remove_handler("on_pubnotice", self.on_pubnotice)
