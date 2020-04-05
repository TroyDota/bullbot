import datetime
import logging
import math
import random
from collections import Counter

import Levenshtein
import requests
from word2number import w2n

from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class TriviaModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Trivia"
    DESCRIPTION = "Trivia!"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="hint_count",
            label="How many hints the user should get before the question is ruined.",
            type="number",
            required=True,
            default=2,
            constraints={"min_value": 0, "max_value": 4},
        ),
        ModuleSetting(
            key="step_delay",
            label="Time between each step (step_delay*(hint_count+1) = length of each question)",
            type="number",
            required=True,
            placeholder="",
            default=10,
            constraints={"min_value": 5, "max_value": 45},
        ),
        ModuleSetting(
            key="default_point_bounty",
            label="Default point bounty per right answer",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 1000},
        ),
        ModuleSetting(
            key="question_delay",
            label="Delay between questions in seconds.",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 600},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

        self.job = None
        self.check_job = None
        self.checkPaused = True

        self.jservice = False
        self.trivia_running = False
        self.last_question = None
        self.question = None
        self.step = 0
        self.last_step = None
        self.deadTrivia = 0
        self.correct_dict = {}

        self.gazCategories = [
            "W_OMEGALUL_W",
            "Vietnam",
            "Video Games",
            "Twitch",
            "Sports",
            "Star Wars",
            "Spongebob",
            "Science",
            "Programming",
            "Music",
            "Memes",
            "Math",
            "Maths",
            "Movies",
            "Languages",
            "History",
            "Geography",
            "General Knowledge",
            "Gachimuchi",
            "Gachi",
            "Emotes",
            "Entertainment",
            "Bees",
            "Country",
            "Books",
            "AdmiralBulldog",
            "D DansGame TA",
            "Country",
            "HTTP",
            "Football",
        ]

        self.bad_phrases = [
            "href=",  # bad phrases for questions
            "Which of these",
            "Which one of these",
            "Which of the following",
            "here is no such thing",
        ]
        self.recent_questions = list()  # List of most recent questions
        self.q_memory = 200  # No. of recent questions to remember
        # Stored winstreak [user name, winstreak]
        self.winstreak = 0
        self.min_streak = 3  # minimum correct answers for a streak
        self.point_bounty = 0
        self.leak_answers = False

    def format_answer(self):
        # Fixme, Ug Th Fa Au Hy Ne
        self.question["answer"] = (
            self.question["answer"]
            .replace("<i>", "")
            .replace("</i>", "")
            .replace("\\", "")
            .replace("(", "")
            .replace(")", "")
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("&", "and")
        )

        self.question["answer"] = self.question["answer"].strip('"').strip(".")

        if self.question["answer"].lower().startswith("a "):
            self.question["answer"] = self.question["answer"][2:]

        elif self.question["answer"].lower().startswith("an "):
            self.question["answer"] = self.question["answer"][3:]

        if self.question["answer"].lower().startswith("the "):
            self.question["answer"] = self.question["answer"][4:]

        self.question["answer"] = self.question["answer"].strip()

        for qWord in self.question["answer"].split(" "):
            try:
                qReplacement = w2n.word_to_num(qWord.lower())
                if qReplacement >= 1000000:
                    continue

                self.question["answer"] = self.question["answer"].replace(qWord, str(qReplacement))
            except:
                pass

    def check_question(self):
        if (
            self.question["question"] not in self.recent_questions
            and self.question["answer"]
            and self.question["question"]
            and not self.bot.is_bad_message(self.question["question"])
            and not self.bot.is_bad_message(self.question["answer"])
            and not any(b in self.question["answer"] for b in self.bad_phrases)
        ):
            self.format_answer()
            try:
                self.question["category"] = self.question["category"].replace("_", " ")
                self.question["category"] = self.question["category"][0].upper() + self.question["category"][1:]

            except KeyError:
                self.question["category"] = self.question["categories"][0].replace("_", " ")
            self.recent_questions.append(self.question["question"])

            self.new_question = True

    def poll_trivia(self):
        if not self.trivia_running:
            return False

        # Check if new question needed
        if self.question is None and (
            self.last_question is None or (utils.now() - self.last_question) >= datetime.timedelta(seconds=11)
        ):

            # GET TRIVIA QUESTION

            self.new_question = False
            while not self.new_question:
                if self.jservice:
                    # Load from jservice database
                    r = requests.get("http://jservice.io/api/random", headers={"User-Agent": self.bot.user_agent})
                    self.question = r.json()[0]
                    self.check_question()

                else:
                    # Load from gazatu and RTD
                    chosenInt = random.randint(0, 10)
                    if chosenInt <= 5:
                        r = requests.get(
                            "http://159.203.60.127/questions?limit=1", headers={"User-Agent": self.bot.user_agent}
                        )
                        self.question = r.json()
                        self.question["category"] = self.question["categories"][0]
                        self.check_question()
                    else:
                        self.gazatuService = True
                        r = requests.get(
                            f"https://api.gazatu.xyz/trivia/questions?count=1&include=[{','.join(self.gazCategories)}]",
                            headers={"User-Agent": self.bot.user_agent},
                        )

                        self.question = r.json()[0]
                        self.check_question()

            # Remove oldest question
            if len(self.recent_questions) > self.q_memory:
                del self.recent_questions[0]

            self.step = 0
            self.last_step = None

        # Is it time for the next step?
        condition = self.last_question is None or utils.now() - self.last_question >= datetime.timedelta(
            seconds=self.settings["question_delay"]
        )
        if (self.last_step is None and condition) or (
            self.last_step is not None
            and utils.now() - self.last_step >= datetime.timedelta(seconds=self.settings["step_delay"])
        ):
            self.last_step = utils.now()
            self.step += 1

            if self.step == 1:
                self.step_announce()
            elif self.step < self.settings["hint_count"] + 2:
                self.step_hint()
            else:
                self.step_end()

    def step_announce(self):
        try:
            if self.leak_answers:
                log.debug(self.question["answer"])

            if self.jservice:
                self.bot.safe_me(
                    f'PogChamp A new question has begun! In the category "{self.question["category"]["title"]}", the question/hint/clue is "{self.question["question"]}" 🤔'
                )
            else:
                self.bot.safe_me(
                    f'PogChamp A new question has begun! In the category "{self.question["category"]}", the question is "{self.question["question"]}" 🤔'
                )
        except:
            self.step = 0
            self.question = None
            pass

    def step_hint(self):
        # find out what % of the answer should be revealed
        full_hint_reveal = int(math.floor(len(self.question["answer"]) / 2))
        current_hint_reveal = int(math.floor(((self.step) / 2.2) * full_hint_reveal))

        hint_arr = []
        hint_chars = 0
        index = 0
        for c in self.question["answer"]:
            if c == " ":
                hint_arr.append(" ")
            else:
                if index < current_hint_reveal:
                    hint_chars += 1
                    hint_arr.append(self.question["answer"][index])
                else:
                    hint_arr.append("_")
            index += 1
        hint_str = "".join(hint_arr)

        if hint_chars == 0 and len(self.question["answer"]) > 1:
            copy_str = self.question["answer"][0]
            copy_str += hint_str[1:]
            hint_str = copy_str
            hint_chars += 1

        if self.question["answer"].isnumeric() and hint_chars == 1 and len(self.question["answer"]) > 3:
            hint_str = self.question["answer"][:2] + hint_str[2:]

        self.bot.safe_me(f'OpieOP Here\'s a hint, "{hint_str}" OpieOP')

    def step_end(self):
        if self.question is not None:
            self.deadTrivia += 1
            self.winstreak = 0
            self.bot.safe_me(
                f'MingLee No one could answer the trivia! The answer was "{self.question["answer"]}" MingLee'
            )
            self.question = None
            self.step = 0
            self.last_question = utils.now()
            with DBManager.create_session_scope() as db_session:
                user = User.find_by_id(db_session, 83460519)
                user.points = user.points + 1

            if self.deadTrivia > 8:
                self.bot.say("Guys? Anyone here? Sadge")
                self.trivia_running = False
                if self.job is not None:
                    self.job.remove()
                    self.job = None

    def check_run(self):
        if self.bot.is_online and self.trivia_running:
            log.debug("Stopping trivia")
            self.stop_trivia(True)

    def command_leak(self, **rest):
        self.leak_answers = not self.leak_answers

    def command_start(self, bot, source, message, **rest):
        if self.trivia_running:
            bot.me(f"{source}, a trivia is already running")
            return

        if bot.is_online:
            bot.whisper(source, "You can't start a trivia when the stream is live.")
            return

        self.trivia_running = True
        self.job = ScheduleManager.execute_every(1, self.poll_trivia)

        try:
            self.point_bounty = int(message)
            if self.point_bounty < 0:
                self.point_bounty = 0
            if source.level < 500:
                self.point_bounty = 20
        except:
            self.point_bounty = self.settings["default_point_bounty"]

        if self.point_bounty > 0:
            self.bot.safe_me(f"The trivia has started! {self.point_bounty} points for each right answer!")
        else:
            self.bot.safe_me("The trivia has started!")

        HandlerManager.add_handler("on_message", self.on_message)

    def stop_trivia(self, source=None):
        if not self.trivia_running and source is not None:
            self.bot.safe_me(f"{source}, no trivia is active right now")
            return

        if self.job is not None:
            self.job.remove()
            self.job = None

        self.trivia_running = False

        self.step_end()
        self.correct_dict = {}

        if self.trivia_running:
            stopOutput = "The trivia has been stopped. The top five participants are: "
            c = Counter(self.correct_dict)
            for player, correct in c.most_common(5):
                stopOutput += f"{player}, with {correct} correct guesses. "

            self.bot.safe_me(stopOutput)

        HandlerManager.remove_handler("on_message", self.on_message)

    def command_stop(self, bot, source, **rest):
        self.stop_trivia(source=source)

    def command_skip(self, bot, **rest):
        if self.question is None:
            bot.say("There is currently no question.")
        else:
            self.question = None
            self.step = 0
            self.last_question = None

    def on_message(self, source, message, whisper, **rest):
        sendMessage = ""
        if message is None or whisper or source.ignored:
            return

        self.deadTrivia = 0
        if self.question:
            right_answer = self.question["answer"].lower()
            user_answer = message.lower()
            if len(right_answer) <= 5:
                correct = right_answer == user_answer
            else:
                ratio = Levenshtein.ratio(right_answer, user_answer)
                correct = ratio >= 0.86

            if correct:
                sendMessage = f"{source} got the answer right! The answer was {self.question['answer']} FeelsGoodMan"

                if self.point_bounty > 0:
                    sendMessage += f" They get {self.point_bounty} points! PogChamp"
                    source.points = source.points + self.point_bounty

                self.question = None
                self.step = 0
                self.last_question = utils.now()
                self.correct_dict[source.username_raw] = self.correct_dict.get(source.username_raw, 0) + 1

                # record winstreak of correct answers for user

                if source != self.winstreak:
                    self.winstreak = 1
                else:
                    self.winstreak += 1
                    if self.winstreak >= 7:
                        sendMessage += f" {source} is on a {self.winstreak} question streak. Get a life FeelsWeirdMan"
                    elif self.winstreak >= self.min_streak:
                        sendMessage += f" {source} is on a streak of {self.winstreak} correct answers Pog"

                self.bot.safe_me(sendMessage)

    def load_commands(self, **options):
        self.commands["trivia"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            commands={
                "start": Command.raw_command(
                    self.command_start, level=100, delay_all=0, delay_user=60, can_execute_with_whisper=True
                ),
                "stop": Command.raw_command(
                    self.command_stop, level=420, delay_all=0, delay_user=0, can_execute_with_whisper=True
                ),
                "skip": Command.raw_command(
                    self.command_skip, level=420, delay_all=0, delay_user=0, can_execute_with_whisper=True
                ),
            },
        )

        self.commands["leakanswers"] = Command.raw_command(
            self.command_leak, level=500, description="Log the answers to stdout"
        )

    def enable(self, bot):
        if bot:
            self.check_job = ScheduleManager.execute_every(10, self.check_run)

        HandlerManager.add_handler("on_quit", self.stop_trivia)

    def disable(self, bot):
        if bot:
            self.check_job.remove()
            self.check_job = None

        HandlerManager.remove_handler("on_quit", self.stop_trivia)
