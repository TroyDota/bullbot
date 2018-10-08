import datetime
import logging

import requests

import pajbot.models
from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)

class ExitLoop(Exception):
    pass

class DotaBetModule(BaseModule):
    AUTHOR = 'DatGuy1'
    ID = __name__.split('.')[-1]
    NAME = 'DotA Betting'
    DESCRIPTION = 'Enables betting on DotA 2 games with !dotabet'
    CATEGORY = 'Game'

    SETTINGS = [
            ModuleSetting(
                key='steam3_id',
                label='Steam 3 ID of streamer (number only)',
                type='number',
                required=True,
                placeholder='',
                default=''),
            ModuleSetting(
                key='api_key',
                label='Steam API Key',
                type='text',
                required=True,
                placeholder='',
                default=''),
            ModuleSetting(
                key='return_pct',
                label='Percent of bet that is returned',
                type='number',
                required=True,
                placeholder='',
                default=200,
                constraints={
                    'min_value': 1,
                    'max_value': 1000,
                    }),
            ]

    def __init__(self):
        super().__init__()
        self.bets = {}
        self.betting_open = False
        self.message_closed = True
        self.isRadiant = False
        self.matchID = 0
        self.oldID = 0

        self.job = ScheduleManager.execute_every(45, self.poll_webapi)
        self.job.pause()

        self.reminder_job = ScheduleManager.execute_every(200, self.reminder_bet)
        self.reminder_job.pause()

        self.finish_job = ScheduleManager.execute_every(60, self.get_game)
        self.finish_job.pause()

    def reminder_bet(self):
        if self.betting_open:
            self.bot.me('monkaS 👉 🕒 place your bets people')
            self.bot.websocket_manager.emit('notification', {'message': 'monkaS 👉 🕒 place your bets people'})
        else:
            if not self.message_closed:
                self.bot.me('The betting for the current game has been closed!')
                self.bot.websocket_manager.emit('notification', {'message': 'The betting for the current game has been <b>closed!</b>'})
                self.message_closed = True

    def spread_points(self, gameResult):
        winners = 0
        losers = 0
        total_winnings = 0
        total_losings = 0

        with DBManager.create_session_scope() as db_session:
            for username in self.bets:
                bet_for_win, betPoints = self.bets[username]
                points = int(betPoints * self.settings['return_pct'] / 100)

                user = self.bot.users.find(username, db_session=db_session)
                if user is None:
                    continue

                # log.debug(gameResult)
                correct_bet = (gameResult == 'win' and bet_for_win is True) or (gameResult == 'loss' and bet_for_win is False)

                if correct_bet:
                    winners += 1
                    total_winnings += points
                    user.points += points + betPoints
                    user.save()
                    self.bot.whisper(user.username, 'You bet {} points on the correct outcome, ' \
                                     'you now have {} points PogChamp'.format(betPoints, user.points))
                else:
                    losers += 1
                    total_losings += betPoints
                    user.save()
                    self.bot.whisper(user.username, 'You bet {} points on the wrong outcome, so you lost it all. :('.format(
                        betPoints))

        resultString = 'The game ended as a {}. {} users won a total of {} points, while {}' \
                       ' lost {} points.'.format(gameResult, winners, total_winnings, losers, total_losings)

        htmlString = 'The game ended as a {}. {} users won a total of {} points, while {}' \
                     ' lost {} points.'.format(gameResult, winners, total_winnings, losers, total_losings)


        # self.bets = {}
        self.betting_open = False
        self.message_closed = True

        self.bot.websocket_manager.emit('notification', {'message': htmlString, 'length': 8})
        self.bot.me(resultString)

    def get_game(self):
        gameResult = 'loss'
        # log.error(self.isRadiant)

        odURL = 'https://api.opendota.com/api/players/{}/recentMatches'.format(self.settings['steam3_id'])
        gameHistory = requests.get(odURL).json()[0]

        if gameHistory['match_id'] != self.oldID:
            self.oldID = gameHistory['match_id']

            if self.isRadiant and gameHistory['radiant_win']:
                gameResult = 'win'
            else:
                if not self.isRadiant and not gameHistory['radiant_win']:
                    gameResult = 'win'
                else:
                    gameResult = 'loss'
            # log.error(gameResult)
            self.spread_points(gameResult)

    def poll_webapi(self):
        serverID = ''

        with open('/srv/admiralbullbot/configs/currentID.txt', 'r') as f:
            serverID = f.read()
        log.error(serverID)
        try:
            serverID = int(serverID)
        except:
            return False

        self.bot.execute_delayed(1, self.get_team, (serverID, ))

        if int(serverID) == 0:
            self.bot.execute_delayed(60, self.close_shit)
            return False

        if self.betting_open:
            log.error('betting open')
            return False

        self.bets = {}
        self.betting_open = True
        self.message_closed = False
        self.bot.websocket_manager.emit('notification', {'message': 'Betting has been opened'})
        self.bot.me('A new game has begun! Vote with !dotabet win/lose POINTS')

    def get_team(self, serverID):
        if not serverID:
            return

        webURL = 'https://api.steampowered.com/IDOTA2MatchStats_570/GetRealtimeStats/v1?' \
                 'server_steam_id={}&key={}'.format(serverID, self.settings['api_key'])
        jsonText = requests.get(webURL).json()

        while not jsonText: # Could bug and not return anything
            jsonText = requests.get(webURL).json()
            if 'teams' not in jsonText:
                jsonText = ''
            if 'teams' in jsonText:
                if 'players' not in jsonText['teams'][0]:
                    jsonText = ''

        try:
            for i in range(2):
                for player in jsonText['teams'][i]['players']:
                    log.error(player['name'])
                    if player['accountid'] == self.settings['steam3_id']:
                        if i == 0:
                            self.isRadiant = True
                        else:
                            self.isRadiant = False
                        raise ExitLoop
        except ExitLoop:
            pass
        log.error(self.isRadiant)

    def command_open(self, **options):
        bot = options['bot']
        message = options['message']

        if message:
            if 'dire' in message:
                self.isRadiant = False
            else:
                self.isRadiant = True

        self.betting_open = True
        self.message_closed = False
        self.job.pause()
        self.jobPaused = True
        
        bot.websocket_manager.emit('notification', {'message': 'Betting has been opened'})
        bot.me('Betting has been opened.')

    def close_shit(self):
        if self.jobPaused:
            return False
        self.betting_open = False
        self.reminder_bet()

    def command_close(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        if message:
            if 'l' in message.lower():
                self.spread_points('loss')
            else:
                self.spread_points('win')
            self.bets = {}
                

        self.betting_open = False
        self.reminder_bet()
        self.job.resume()
        self.jobPaused = False

    def command_restart(self, **options):
        bot = options['bot']
        message = options['message']
        source = options['source']
        reason = ''

        if not message:
            reason = 'No reason given EleGiggle'
        else:
            reason = message

        with DBManager.create_session_scope() as db_session:
            for username in self.bets:
                bet_for_win, betPoints = self.bets[username]
                user = self.bot.users.find(username, db_session=db_session)
                if not user:
                    continue

                user.points += betPoints
                bot.whisper(user.username, 'Your {} points bet has been refunded. The reason given is: ' \
                                           '{}'.format(betPoints, reason))

        self.bets = {}
        self.betting_open = False
        self.message_closed = True

        if options['message']:
            self.betting_open = True
            self.message_closed = False

        bot.me('All your bets have been refunded and betting has been restarted.')

    def command_resetbet(self, **options):
        self.bets = {}
        bot.say('The bets have been reset :)')

    def command_bet(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        if message is None:
            return False

        if not self.betting_open:
            bot.whisper(source.username, 'Betting is not currently open. Wait until the next game :\\')
            return False

        msg_parts = message.split(' ')
        if msg_parts == 0:
            bot.whisper(source.username, 'Usage: !dotabet win/lose POINTS')
            return False

        outcome = msg_parts[0].lower()
        bet_for_win = False

        if 'w' in outcome:
            bet_for_win = True
        elif 'l' in outcome:
            bet_for_win = False
        else:
            bot.whisper(source.username, 'Invalid bet. Usage: !dotabet win/loss POINTS')
            return False

        points = 0
        try:
            points = int(msg_parts[1])
            if points > 1000:
                points = 1000

        except (IndexError, ValueError, TypeError):
            bot.whisper(source.username, 'Invalid bet. Usage: !dotabet win/loss POINTS')
            return False

        if points < 0:
            bot.whisper(source.username, 'You cannot bet negative points.')
            return False

        if not source.can_afford(points):
            bot.whisper(source.username, 'You don\'t have {} points to bet'.format(points))
            return False

        if source.username in self.bets:
            bot.whisper(source.username, 'You have already bet on this game. Wait until the next game starts!')
            return False

        source.points -= points
        self.bets[source.username] = (bet_for_win, points)
        bot.whisper(source.username, 'You have bet {} points on this game resulting in a {}.'.format(points, 'win' if bet_for_win else 'loss'))

    def load_commands(self, **options):
        self.commands['dotabet'] = pajbot.models.command.Command.raw_command(self.command_bet,
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            description='Bet points',
            examples=[
                pajbot.models.command.CommandExample(None, 'Bet 69 points on a win',
                    chat='user:!dotabet win 69\n'
                    'bot>user: You have bet 69 points on this game resulting in a win.',
                    description='Bet that the streamer will win for 69 points').parse(),
                ],
            )
        self.commands['bet'] = self.commands['dotabet']

        self.commands['openbet'] = pajbot.models.command.Command.raw_command(self.command_open,
            level = 500,
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            description='Open bets',
            )
        self.commands['restartbet'] = pajbot.models.command.Command.raw_command(self.command_restart,
            level = 500,
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            description='Restart bets',
            )
        self.commands['closebet'] = pajbot.models.command.Command.raw_command(self.command_close,
            level = 500,
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            description='Close bets',
            )
        self.commands['resetbet'] = pajbot.models.command.Command.raw_command(self.command_resetbet,
            level = 500,
            can_execute_with_whisper=True,
            description='Reset bets',
            )


    def enable(self, bot):
        if bot:
            self.job.resume()
            self.reminder_job.resume()
            self.finish_job.resume()
        self.bot = bot

    def disable(self, bot):
        if bot:
            self.job.pause()
            self.reminder_job.pause()
            self.finish_job.pause()
