import logging

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
    ]

    def __init__(self, bot):
        super().__init__(bot)

    def on_pubnotice(self, channel, msg_id, message):
        if msg_id == "subs_on":
            self.bot.me(self.get_phrase("message_subonly"))
        elif msg_id == "subs_off":
            self.bot.me(self.get_phrase("message_suboff"))

    def enable(self, bot):
        if not bot:
            return

        HandlerManager.add_handler("on_pubnotice", self.on_pubnotice)

    def disable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        HandlerManager.remove_handler("on_pubnotice", self.on_pubnotice)
