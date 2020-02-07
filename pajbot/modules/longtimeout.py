import logging
from datetime import timedelta

from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.longtimeout import LongTimeout
from pajbot.models.user import User
from pajbot.modules import BaseModule

log = logging.getLogger(__name__)


class LongTimeoutModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Long Timeout"
    DESCRIPTION = "Do an extra-long timeout"
    CATEGORY = "Feature"

    def __init__(self, bot):
        super().__init__(bot)
        self.checkJob = None
        self.mysqlFormat = "%Y-%m-%d %H:%M:%S"

    def check_retimeout(self):
        with DBManager.create_session_scope() as db_session:
            timeoutList = db_session.query(LongTimeout).all()
            timeNow = utils.now()
            for timeoutItem in timeoutList:
                timeoutUser = timeoutItem.user
                timeoutEnd = timeoutItem.timeout_recent_end
                overallStart = timeoutItem.timeout_start
                overallEnd = timeoutItem.timeout_end

                if timeNow > overallEnd:
                    self.bot.whisper_login(
                        timeoutItem.timeout_author,
                        f"{timeoutUser}'s timeout of {round((overallEnd - overallStart).seconds / 3600, 2)} hours has ended.",
                    )
                    db_session.delete(timeoutItem)
                    continue

                if timeoutEnd < timeNow:
                    timeoutDuration = 1209600
                    if (overallEnd - timeNow).days < 14:
                        timeoutDuration = (overallEnd - timeNow).seconds

                    timeoutHours = round(float(timeoutDuration / 3600), 2)
                    timeoutItem.timeout_recent_end = timeNow + timedelta(seconds=timeoutDuration)
                    self.bot.whisper_login(
                        timeoutItem.timeout_author, f"Timing out {timeoutUser} for an additional {timeoutHours} hours"
                    )
                    self.bot._timeout(
                        timeoutUser,
                        timeoutDuration,
                        f"Timed out {timeoutUser} for an additional {timeoutHours} hours, per {timeoutItem.timeout_author}'s !longtimeout",
                    )
                    db_session.add(timeoutItem)

    def long_timeout(self, bot, message, source, **options):
        errorString = "Invalid usage. !longtimeout user days"
        daysDuration = 0

        if not message or len(message.split(" ")) < 2:
            bot.whisper(source, errorString)
            return False

        splitMsg = message.split(" ")

        try:
            daysDuration = int(splitMsg[1])
            timeoutDuration = daysDuration * 86400
            if timeoutDuration > 1209600:
                timeoutDuration = 1209600

            nowTime = utils.now()
            endTime = nowTime + timedelta(days=daysDuration)
            with DBManager.create_session_scope() as db_session:
                badPerson = User.find_or_create_from_user_input(db_session, bot.twitch_helix_api, splitMsg[0])

                if badPerson.moderator:
                    bot.whisper(source, "You can't timeout mods")
                    return False

                if badPerson.level >= 420:
                    bot.whisper(source, f"{badPerson}'s level is too high, you can't time them out.")
                    return False

                if db_session.query(LongTimeout).filter(LongTimeout.user_id == badPerson.id).count() != 0:
                    bot.whisper(source, f"{badPerson} already exists in the database")
                    return False

                longtimeout = LongTimeout(
                    user_id=badPerson.id, timeout_start=nowTime, timeout_end=endTime, timeout_author=source.name
                )

                db_session.add(longtimeout)

                bot._timeout(badPerson, timeoutDuration, f"Timed out by {source} for {daysDuration} days total")
                bot.whisper(source, f"Timed out {badPerson} for {daysDuration} days, per your !longtimeout")

        except ValueError:
            bot.whisper(source, errorString)
            return False
        except Exception as e:
            log.error(e)

    def list_timeouts(self, bot, source, **rest):
        with DBManager.create_session_scope() as db_session:
            timeoutList = db_session.query(LongTimeout).all()

            if not timeoutList:
                bot.whisper(source, "There are currently no long timeouts.")
                return True

            listString = ""
            for timeoutItem in timeoutList:
                # log.debug(timeoutItem.__dict__)
                listString += f"{timeoutItem.user}: {timeoutItem.timeout_end}, "

            bot.whisper(source, listString[:-2])

    def remove_timeout(self, bot, message, source, **rest):
        if not message:
            bot.whisper(source, "Invalid usage. !removetimeout user")
            return False

        with DBManager.create_session_scope() as db_session:
            targetUser = User.find_or_create_from_user_input(db_session, bot.twitch_helix_api, message.split()[0])
            remTimeout = db_session.query(LongTimeout).filter_by(user_id=targetUser.id).one_or_none()
            if not remTimeout:
                bot.whisper(source, f"User '{targetUser}' doesn't exist. See !listtimeouts")
                return False

            bot.whisper(
                source,
                f"{remTimeout.user}'s timeout of {(remTimeout.timeout_end - remTimeout.timeout_start).days} days has been cancelled.",
            )
            db_session.delete(remTimeout)

    def load_commands(self, **options):
        from pajbot.models.command import Command
        from pajbot.models.command import CommandExample

        self.commands["longtimeout"] = Command.raw_command(
            self.long_timeout,
            level=500,
            description="Timeout someone for a duration longer than Twitch allows",
            can_execute_with_whispers=True,
            examples=[
                CommandExample(
                    None,
                    "Timeout syndereN for three weeks",
                    chat="user:!longtimeout synderen 21\n" "bot>user:Timed out syndereN for 21 days",
                ).parse()
            ],
        )

        self.commands["listtimeouts"] = Command.raw_command(
            self.list_timeouts,
            level=500,
            description="List pending timeouts",
            can_execute_with_whispers=True,
            examples=[
                CommandExample(
                    None,
                    "Get wben timeouts expire",
                    chat="user:!listtimeouts\n" "bot>user:syndereN: 2019-05-12 08:31:09",
                ).parse()
            ],
        )

        self.commands["removetimeout"] = Command.raw_command(
            self.remove_timeout,
            level=500,
            description="Remove unfulfilled timeout",
            can_execute_with_whispers=True,
            examples=[
                CommandExample(
                    None,
                    "Cancel syndereN's long timeout",
                    chat="user:!removetimeout syndereN\n" "bot>user:Successfully cancelled syndereN's 14 day timeout",
                ).parse()
            ],
        )

    def enable(self, bot):
        if not bot:
            return

        self.checkJob = ScheduleManager.execute_every(30, self.check_retimeout)

    def disable(self, bot):
        if not bot:
            return

        self.checkJob.remove()
