import websocket
import json
import threading
import logging

from pajbot.apiwrappers.authentication.token_manager import UserAccessTokenManager, NoTokenError
from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.user import UserBasics

log = logging.getLogger("pajbot")


class PubSubManager:
    def __init__(self, bot):
        self.bot = bot
        self.streamerID = bot.streamer_user_id

        self.accessTokenManager = UserAccessTokenManager(
            api=bot.twitch_id_api, redis=RedisManager.get(), username=bot.streamer, user_id=self.streamerID
        )

        self.connect()

    def quit(self):
        self.wsConn.keep_running = False

    def connect(self):
        self.wsConn = websocket.WebSocketApp(
            "wss://pubsub-edge.twitch.tv",
            on_message=self.onMessage,
            on_error=self.onError,
            on_open=self.onOpen,
            on_close=self.onClose,
        )

        self.wsConn.keep_running = True
        self.runThread = threading.Thread(target=self.wsConn.run_forever)
        self.runThread.daemon = True
        self.runThread.start()

    def pingPS(self):
        self.wsConn.send(json.dumps({"type": "PING"}))

    def onMessage(self, ws, message):
        parsedMain = json.loads(message)

        if parsedMain["type"] == "RECONNECT":
            log.info("Reconnecting PubSub...")
            self.bot.execute_delayed(3, self.connect)
            return
        elif parsedMain["type"] == "RESPONSE":
            if parsedMain["error"]:
                log.error(f"Error with PubSub: {parsedMain['error']}")
            return
        elif parsedMain["type"] != "MESSAGE":
            return

        parsedJson = json.loads(parsedMain["data"]["message"])
        if parsedJson["type"] == "reward-redeemed":
            userDict = parsedJson["data"]["redemption"]["user"]
            HandlerManager.trigger(
                "on_redeem",
                redeemer=UserBasics(userDict["id"], userDict["login"], userDict["display_name"]),
                redeemed_id=parsedJson["data"]["redemption"]["reward"]["id"],
                user_input=parsedJson["data"]["redemption"]["user_input"] or "",
            )

    def onError(self, ws, error):
        log.exception(error)

    def onClose(self, ws):
        log.info("PubSub closed. Reconnecting...")
        self.heartbeatJob.remove()
        self.heartbeatJob = None
        self.wsConn.keep_running = False
        self.bot.execute_delayed(3, self.connect)

    def onOpen(self, ws):
        log.info("PubSub opened")
        self.pingPS()
        self.heartbeatJob = ScheduleManager.execute_every(60, lambda: self.bot.execute_now(self.pingPS))
        self.listenTopic(f"channel-points-channel-v1.{self.bot.streamer_user_id}")

    def listenTopic(self, topicName):
        authToken = ""

        try:
            authToken = self.accessTokenManager.token.access_token
        except NoTokenError:
            log.warning(
                "Cannot use PubSub because no streamer token is present. Please have the streamer log in with the /streamer_login web route to enable PubSub."
            )
            return

        payload = {"type": "LISTEN", "data": {"topics": [topicName], "auth_token": authToken}}
        log.info(f"Subscribing to: {topicName}")
        self.wsConn.send(json.dumps(payload))
