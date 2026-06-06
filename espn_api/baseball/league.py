import datetime
import time
import json
import math
from typing import List, Tuple, Union

from ..base_league import BaseLeague
from .team import Team
from .player import Player
from .matchup import Matchup
from .box_score import BoxScore, H2HCategoryBoxScore, H2HPointsBoxScore
from .activity import Activity
from .constant import ACTIVITY_MAP, get_position_filter_slot_ids

class League(BaseLeague):
    '''Creates a League instance for Public/Private ESPN league'''

    ScoreTypes = {'H2H_CATEGORY': H2HCategoryBoxScore, 'H2H_POINTS': H2HPointsBoxScore}

    def __init__(self, league_id: int, year: int, espn_s2=None, swid=None, fetch_league=True, debug=False):
        super().__init__(league_id=league_id, year=year, sport='mlb', espn_s2=espn_s2, swid=swid, debug=debug)

        self._set_scoring_class = lambda scoring_type: League.ScoreTypes.get(scoring_type, BoxScore)

        self.scoring_type = None
        self._box_score_class = None

        if fetch_league:
            self.fetch_league()
        if self._box_score_class is None:
            self._box_score_class = self._set_scoring_class(self.scoring_type)

    def fetch_league(self):
        data = self._fetch_league()
        self.scoring_type = data['settings']['scoringSettings']['scoringType']
        self._fetch_teams(data)
        self._box_score_class = self._set_scoring_class(self.scoring_type)
        super()._fetch_draft()

    def _fetch_league(self):
        data = super()._fetch_league()
        self._fetch_players()
        return data

    def _fetch_teams(self, data):
        '''Fetch teams in league'''
        super()._fetch_teams(data, TeamClass=Team)

        # replace opponentIds in schedule with team instances
        for team in self.teams:
            team.division_name = self.settings.division_map.get(team.division_id, '')
            for week, matchup in enumerate(team.schedule):
                for opponent in self.teams:
                    if matchup.away_team == opponent.team_id:
                        matchup.away_team = opponent
                    if matchup.home_team == opponent.team_id:
                        matchup.home_team = opponent

    def refresh(self):
        '''Gets latest league data. This can be used instead of creating a new League class each week'''
        data = super()._fetch_league()
        self.scoring_type = data['settings']['scoringSettings']['scoringType']
        self._fetch_teams(data)
        self._box_score_class = self._set_scoring_class(self.scoring_type)

    def load_roster_week(self, week: int) -> None:
        '''Sets Teams Roster for a Certain Week'''
        params = {
            'view': 'mRoster',
            'scoringPeriodId': week
        }
        data = self.espn_request.league_get(params=params)

        team_roster = {}
        for team in data['teams']:
            team_roster[team['id']] = team['roster']

        for team in self.teams:
            roster = team_roster[team.team_id]
            team._fetch_roster(roster, self.year)

    def player_info(self, name: str = None, playerId: Union[int, list] = None) -> Union[Player, List[Player]]:
        '''Returns Player class if name found'''
        if name:
            playerId = self.player_map.get(name)
        if playerId is None or isinstance(playerId, str):
            return None
        if not isinstance(playerId, list):
            playerId = [playerId]

        data = self.espn_request.get_player_card(playerId, self.finalScoringPeriod)
        if len(data['players']) == 1:
            return Player(data['players'][0], self.year)
        if len(data['players']) > 1:
            return [Player(player, self.year) for player in data['players']]

    def standings(self) -> List[Team]:
        standings = sorted(self.teams, key=lambda x: x.final_standing if x.final_standing != 0 else x.standing, reverse=False)
        return standings

    def scoreboard(self, matchupPeriod: int = None) -> List[Matchup]:
        '''Returns list of matchups for a given matchup period'''
        if not matchupPeriod:
            matchupPeriod=self.currentMatchupPeriod

        params = {
            'view': 'mMatchup',
        }
        data = self.espn_request.league_get(params=params)
        schedule = data['schedule']
        matchups = [Matchup(matchup) for matchup in schedule if matchup['matchupPeriodId'] == matchupPeriod]

        for team in self.teams:
            for matchup in matchups:
                if matchup.home_team == team.team_id:
                    matchup.home_team = team
                elif matchup.away_team == team.team_id:
                    matchup.away_team = team

        return matchups

    def recent_activity(self, size: int = 25, msg_type: str = None, offset: int = 0) -> List[Activity]:
        '''Returns a list of recent league activities (Add, Drop, Trade)'''
        if self.year < 2019:
            raise Exception('Cant use recent activity before 2019')

        msg_types = [178,180,179,239,181,244]
        if msg_type in ACTIVITY_MAP:
            msg_types = [ACTIVITY_MAP[msg_type]]
        params = {
            'view': 'kona_league_communication'
        }

        filters = {"topics":{"filterType":{"value":["ACTIVITY_TRANSACTIONS"]},"limit":size,"limitPerMessageSet":{"value":25},"offset":offset,"sortMessageDate":{"sortPriority":1,"sortAsc":False},"sortFor":{"sortPriority":2,"sortAsc":False},"filterIncludeMessageTypeIds":{"value":msg_types}}}
        headers = {'x-fantasy-filter': json.dumps(filters)}
        data = self.espn_request.league_get(extend='/communication/', params=params, headers=headers)
        data = data['topics']
        activity = [Activity(topic, self.player_map, self.get_team_data) for topic in data]

        return activity

    def free_agents(self, week: int=None, size: int=50, position: str=None, position_id: int=None) -> List[Player]:
        '''Returns a List of Free Agents for a Given Week\n
        Should only be used with most recent season'''

        if self.year < 2019:
            raise Exception('Cant use free agents before 2019')
        if not week:
            week = self.current_week

        slot_filter = []
        if position:
            slot_filter.extend(get_position_filter_slot_ids(position))
        if position_id:
            slot_filter.append(position_id)

        if slot_filter:
            slot_filter = list(dict.fromkeys(slot_filter))


        params = {
            'view': 'kona_player_info',
            'scoringPeriodId': week,
        }
        filters = {"players":{"filterStatus":{"value":["FREEAGENT","WAIVERS"]},"filterSlotIds":{"value":slot_filter},"limit":size,"sortPercOwned":{"sortPriority":1,"sortAsc":False},"sortDraftRanks":{"sortPriority":100,"sortAsc":True,"value":"STANDARD"}}}
        headers = {'x-fantasy-filter': json.dumps(filters)}

        data = self.espn_request.league_get(params=params, headers=headers)
        players = data['players']

        return [Player(player, self.year) for player in players]

    def box_scores(self, matchup_period: int = None, scoring_period: int = None) -> List[Union[BoxScore, H2HCategoryBoxScore]]:
        '''Returns list of box score for a given matchup or scoring period'''
        if self.year < 2019:
            raise Exception('Cant use box score before 2019')

        matchup_id = self.currentMatchupPeriod
        scoring_id = self.current_week
        if matchup_period and scoring_period:
            matchup_id = matchup_period
            scoring_id = scoring_period
        elif matchup_period and matchup_period < matchup_id:
            matchup_id = matchup_period

        params = {
            'view': ['mMatchupScore', 'mScoreboard', 'mBoxscore'],
            'scoringPeriodId': scoring_id
        }

        filters = {"schedule":{"filterMatchupPeriodIds":{"value":[matchup_id]}}}
        headers = {'x-fantasy-filter': json.dumps(filters)}
        data = self.espn_request.league_get(params=params, headers=headers)
        pro_schedule = self._get_pro_schedule(scoring_id)

        # Pass scoring items so H2HCategoryBoxScore can recompute from roster data
        scoring_items = self.settings._raw_scoring_settings.get('scoringItems', [])

        schedule = data['schedule']
        box_data = [self._box_score_class(matchup, pro_schedule, self.year, scoring_id, scoring_items=scoring_items) for matchup in schedule]

        for team in self.teams:
            for matchup in box_data:
                if matchup.home_team == team.team_id:
                    matchup.home_team = team
                elif matchup.away_team == team.team_id:
                    matchup.away_team = team
        return box_data

    # --- Write / transaction support -----------------------------------------
    # Every mutation is a POST to the single /transactions/ endpoint; only the body
    # changes (see docs/writes/00-BRIEF.md and the WRITE_API_REFERENCE spec).
    # Each method accepts dry_run: when True it returns the exact payload dict without
    # POSTing, so callers can preview/confirm the identical body that will execute.

    def _build_transaction(self, team_id: int, txn_type: str, items: list,
                           execution_type: str = 'EXECUTE', **extra) -> dict:
        '''Assemble the shared transaction envelope. extra carries op-specific keys
        (bidAmount, expirationDate, comment, relatedTransactionId).'''
        cookies = self.espn_request.cookies or {}
        body = {
            'isLeagueManager': False,
            'teamId': team_id,
            'type': txn_type,
            'memberId': cookies.get('SWID'),
            'scoringPeriodId': self.scoringPeriodId,
            'executionType': execution_type,
            'items': items,
        }
        body.update(extra)
        return body

    def _post_transaction(self, payload: dict) -> dict:
        return self.espn_request.league_post(payload)

    def set_lineup_moves(self, team_id: int, moves: list, dry_run: bool = False) -> dict:
        '''moves: list of (playerId, fromLineupSlotId, toLineupSlotId). A swap is two moves.'''
        items = [
            {
                'playerId': player_id,
                'type': 'LINEUP',
                'fromLineupSlotId': from_slot,
                'toLineupSlotId': to_slot,
            }
            for (player_id, from_slot, to_slot) in moves
        ]
        payload = self._build_transaction(team_id, 'ROSTER', items)
        return payload if dry_run else self._post_transaction(payload)

    def add_drop_player(self, team_id: int, add_player_id: int = None,
                        drop_player_id: int = None, dry_run: bool = False) -> dict:
        '''Free-agent ADD and/or DROP in one transaction. ADD uses toTeamId; DROP uses fromTeamId.'''
        items = []
        if add_player_id is not None:
            items.append({'playerId': add_player_id, 'type': 'ADD', 'toTeamId': team_id})
        if drop_player_id is not None:
            items.append({'playerId': drop_player_id, 'type': 'DROP', 'fromTeamId': team_id})
        payload = self._build_transaction(team_id, 'FREEAGENT', items)
        return payload if dry_run else self._post_transaction(payload)

    def waiver_claim(self, team_id: int, add_player_id: int, drop_player_id: int = None,
                     bid_amount=None, dry_run: bool = False) -> dict:
        '''Waiver claim (lands PENDING). Same item shape as free agents; bid_amount=None for no-FAAB.'''
        items = [{'playerId': add_player_id, 'type': 'ADD', 'toTeamId': team_id}]
        if drop_player_id is not None:
            items.append({'playerId': drop_player_id, 'type': 'DROP', 'fromTeamId': team_id})
        payload = self._build_transaction(team_id, 'WAIVER', items, bidAmount=bid_amount)
        return payload if dry_run else self._post_transaction(payload)

    def propose_trade(self, from_team_id: int, to_team_id: int, send_player_ids: list,
                      receive_player_ids: list, comment: str = '',
                      expiration_date: str = None, dry_run: bool = False) -> dict:
        '''Propose a trade (lands PENDING, returns a proposal id). send = players leaving
        from_team; receive = players coming from to_team.'''
        items = []
        for player_id in (send_player_ids or []):
            items.append({'playerId': player_id, 'type': 'TRADE',
                          'fromTeamId': from_team_id, 'toTeamId': to_team_id})
        for player_id in (receive_player_ids or []):
            items.append({'playerId': player_id, 'type': 'TRADE',
                          'fromTeamId': to_team_id, 'toTeamId': from_team_id})
        if expiration_date is None:
            expiration_date = (
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)
            ).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        payload = self._build_transaction(from_team_id, 'TRADE_PROPOSAL', items,
                                          expirationDate=expiration_date, comment=comment)
        return payload if dry_run else self._post_transaction(payload)

    def cancel_trade(self, team_id: int, related_transaction_id: str,
                     dry_run: bool = False) -> dict:
        '''Withdraw a pending trade proposal you created.'''
        payload = self._build_transaction(team_id, 'TRADE_PROPOSAL', [],
                                          execution_type='CANCEL',
                                          relatedTransactionId=related_transaction_id)
        return payload if dry_run else self._post_transaction(payload)
