import logging
import threading

from socketIO_client_nexus import SocketIO

from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class asyncSocketIO:
    def __init__(self, bot, settings):
        self.bot = bot
        self.settings = settings

        try:
            self.receiveEventsThread._stop
        except:
            pass

        self.socketIO = SocketIO("https://sockets.streamlabs.com", params={"token": settings["socketToken"]})
        self.socketIO.on("event", self.onEvent)
        self.socketIO.on("disconnect", self.onDisconnect)

        self.receiveEventsThread = threading.Thread(target=self._receiveEventsThread)
        self.receiveEventsThread.daemon = True
        self.receiveEventsThread.start()

    def onEvent(self, *args):
        self.updatePoints(self.settings["usdValue"], args)

    def onDisconnect(self, *args):
        log.error("Socket disconnected. Donations no longer monitored")
        ScheduleManager.execute_delayed(15, self.reset)

    def updatePoints(self, usdPoints, args):
        if args[0]["type"] != "donation":
            return False

        donation = args[0]["message"][0]

        if "historical" in donation:
            return False

        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, donation["name"])
            if user is None:
                return False

            finalValue = int(
                float(donation["formatted_amount"][1:]) * int(usdPoints)
            )  # formatted_amount changes to USD

            user.points = user.points + finalValue
            self.bot.whisper(user, f"You have been given {finalValue} points due to a donation in your name")

    def _receiveEventsThread(self):
        self.socketIO.wait()

    @classmethod
    def reset(cls):
        bot = cls.bot
        settings = cls.settings

        cls.instance = None
        cls.instance = asyncSocketIO(bot, settings)


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

        asyncSocketIO(bot, self.settings)
