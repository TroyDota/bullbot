import logging

from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager
from pajbot.models.user import User

log = logging.getLogger(__name__)


class DonationPointsModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Donate for points"
    DESCRIPTION = "Users can donate to receive points."
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(key="socketToken", label="Socket token", type="text", required=True),
        ModuleSetting(key="usdValue", label="1 USD equals how many points", type="number", required=True),
    ]

    def enable(self, bot):
        if not bot:
            return

        HandlerManager.add_handler("donation", self.updatePoints)

    def disable(self, bot):
        if not bot:
            return

        HandlerManager.remove_handler("donation", self.updatePoints)

    def updatePoints(self, donation):
        if "historical" in donation:
            return False

        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, donation["name"])
            if user is None:
                return False

            finalValue = int(
                float(donation["formatted_amount"][1:]) * int(self.settings["usdValue"])
            )  # formatted_amount changes to USD

            user.points = user.points + finalValue
            self.bot.whisper(user, f"You have been given {finalValue} points due to a donation in your name")
