from .constant import POSITION_MAP, PRO_TEAM_MAP, STATS_MAP
from .utils import json_parsing
import pdb


JUNK_DISPLAY_POSITIONS = {'BE', 'IL', 'UTIL', 'IF'}
DISPLAY_POSITION_PRIORITY = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'LF', 'CF', 'RF', '2B/SS', '1B/3B', 'P']


def _extract_player_data(data):
    return data.get('playerPoolEntry', {}).get('player') or data.get('player') or data


def _map_default_position(default_position_id):
    if default_position_id is None:
        return ''
    return POSITION_MAP.get(default_position_id - 1, default_position_id - 1)


def _map_eligible_slots(eligible_slots):
    return [POSITION_MAP.get(slot_id, slot_id) for slot_id in eligible_slots]


def _display_position(default_position_id, eligible_slots):
    mapped_slots = _map_eligible_slots(eligible_slots)
    useful_slots = [slot for slot in mapped_slots if slot not in JUNK_DISPLAY_POSITIONS]

    if 'SP' in useful_slots and 'RP' in useful_slots:
        return 'SP/RP'
    if 'SP' in useful_slots:
        return 'SP'
    if 'RP' in useful_slots:
        return 'RP'

    for position in DISPLAY_POSITION_PRIORITY:
        if position in useful_slots:
            return position

    default_position = _map_default_position(default_position_id)
    if default_position and default_position not in JUNK_DISPLAY_POSITIONS:
        return default_position

    if useful_slots:
        return useful_slots[0]
    return default_position


class Player(object):
    '''Player are part of team'''
    def __init__(self, data, year):
        player = _extract_player_data(data)

        self.name = player.get('fullName', json_parsing(data, 'fullName'))
        self.playerId = player.get('id', json_parsing(data, 'id'))
        self.position = _display_position(player.get('defaultPositionId'), player.get('eligibleSlots', []))
        self.lineupSlot = POSITION_MAP.get(data.get('lineupSlotId'), '')
        self.eligibleSlots = _map_eligible_slots(player.get('eligibleSlots', []))  # if position isn't in position map, just use the position id number
        self.acquisitionType = json_parsing(data, 'acquisitionType')
        pro_team_id = player.get('proTeamId', json_parsing(data, 'proTeamId'))
        self.proTeam = PRO_TEAM_MAP.get(pro_team_id, pro_team_id)
        self.injuryStatus = player.get('injuryStatus', json_parsing(data, 'injuryStatus'))
        self.status = data.get('status', player.get('status', json_parsing(data, 'status')))
        self.stats = {}

        self.injuryStatus = player.get('injuryStatus', self.injuryStatus)
        self.injured = player.get('injured', False)
        self.percent_owned = round(player.get('ownership', {}).get('percentOwned', -1), 2)
        self.percent_started = round(player.get('ownership', {}).get('percentStarted', -1), 2)

        # add available stats
        player_stats = player.get('stats', [])
        for stats in player_stats:
            stats_split_type = stats.get('statSplitTypeId')
            if stats.get('seasonId') != year or (stats_split_type != 0 and stats_split_type != 5):
                continue
            stats_breakdown = stats.get('stats') or stats.get('appliedStats', {})
            breakdown = {STATS_MAP.get(int(k), k):v for (k,v) in stats_breakdown.items()}
            points = round(stats.get('appliedTotal', 0), 2)
            scoring_period = stats.get('scoringPeriodId')
            stat_source = stats.get('statSourceId')
            # TODO update stats to include stat split type (0: Season, 1: Last 7 Days, 2: Last 15 Days, 3: Last 30, 4: ??, 5: ?? Used in Box Scores)
            (points_type, breakdown_type) = ('points', 'breakdown') if stat_source == 0 else ('projected_points', 'projected_breakdown')
            if self.stats.get(scoring_period):
                self.stats[scoring_period][points_type] = points
                self.stats[scoring_period][breakdown_type] = breakdown
            else:
                self.stats[scoring_period] = {points_type: points, breakdown_type: breakdown}
        self.total_points = self.stats.get(0, {}).get('points', 0)
        self.projected_total_points = self.stats.get(0, {}).get('projected_points', 0)
            
    def __repr__(self):
        return 'Player(%s)' % (self.name, )
