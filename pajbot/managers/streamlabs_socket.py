import threading
import logging

from socketIO_client_nexus import SocketIO

from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.user import User


log = logging.getLogger(__name__)


class StreamLabsSocket:
    def __init__(self, token):
        self.token = token

        try:
            self.receiveEventsThread._stop
        except:
            pass

        self.socketIO = SocketIO("https://sockets.streamlabs.com", params={"token": token})
        self.socketIO.on("event", self.onEvent)
        self.socketIO.on("disconnect", self.onDisconnect)

        self.receiveEventsThread = threading.Thread(target=self._receiveEventsThread)
        self.receiveEventsThread.daemon = True
        self.receiveEventsThread.start()

    def onEvent(self, *args):
        data = args[0]
        if "message" in data and "event" in data["message"]:
            if data["message"]["event"] == "pop":  # new song request pause : pause spotify
                username = data["message"]["media"]["action_by"]
                title = data["message"]["media"]["media_title"]
                HandlerManager.trigger("pause_spotify", title=title, username=username)
            elif data["message"]["event"] == "play":  # on resume:
                HandlerManager.trigger("change_state", state=False)
            elif data["message"]["event"] == "pause":  # on pause:
                HandlerManager.trigger("change_state", state=True)
            elif (
                data["message"]["event"] == "next" and data["message"]["media"] is None
            ):  # no new songs requested : resume spotify
                HandlerManager.trigger("resume_spotify")
        if args[0]["type"] == "donation":
            HandlerManager.trigger("donation", donation=args[0]["message"][0])

    def onDisconnect(self, *args):
        log.error("Socket disconnected. Donations no longer monitored")
        ScheduleManager.execute_delayed(15, self.reset)

    def _receiveEventsThread(self):
        self.socketIO.wait()

    @classmethod
    def reset(cls):
        token = cls.token

        cls.instance = None
        cls.instance = StreamLabsSocket(token)
