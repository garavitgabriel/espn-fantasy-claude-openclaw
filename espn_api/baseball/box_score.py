from abc import ABC, abstractmethod
from .box_player import BoxPlayer

from .constant import STATS_MAP

# Stat IDs needed to compute rate stats from counting stats
_BATTING_COUNTING = {0: 'AB', 1: 'H', 8: 'TB', 10: 'B_BB', 12: 'HBP', 13: 'SF'}
_PITCHING_COUNTING = {34: 'OUTS', 37: 'P_H', 39: 'P_BB', 45: 'ER'}
_BENCH_SLOT_IDS = {16, 17}  # BE and IL


def _aggregate_roster_stats(team_data, scoring_cat_ids):
    """Aggregate player stats from rosterForMatchupPeriod for active lineup players.

    Returns a dict {stat_id: value} for all scoring categories.
    """
    roster = team_data.get('rosterForMatchupPeriod', {}).get('entries', [])
    if not roster:
        return None

    # Collect all stat IDs we need (scoring cats + raw counting stats for rate computation)
    counting = {}
    for entry in roster:
        if entry.get('lineupSlotId', -1) in _BENCH_SLOT_IDS:
            continue
        pinfo = entry.get('playerPoolEntry', {}).get('player', {})
        for s in pinfo.get('stats', []):
            sv = s.get('stats', {})
            for stat_id_str, val in sv.items():
                if not isinstance(val, (int, float)):
                    continue
                sid = int(stat_id_str)
                counting[sid] = counting.get(sid, 0) + val

    # Build result: counting stats are summed directly, rate stats are recomputed
    result = {}
    ab = counting.get(0, 0)
    hits = counting.get(1, 0)
    bb = counting.get(10, 0)
    hbp = counting.get(12, 0)
    sf = counting.get(13, 0)
    tb = counting.get(8, 0)
    pa = ab + bb + hbp + sf
    outs = counting.get(34, 0)
    ip = outs / 3.0

    for sid in scoring_cat_ids:
        if sid == 2:    # AVG
            result[sid] = hits / ab if ab else 0
        elif sid == 17:  # OBP
            result[sid] = (hits + bb + hbp) / pa if pa else 0
        elif sid == 9:   # SLG
            result[sid] = tb / ab if ab else 0
        elif sid == 18:  # OPS
            obp = (hits + bb + hbp) / pa if pa else 0
            slg = tb / ab if ab else 0
            result[sid] = obp + slg
        elif sid == 41:  # WHIP
            result[sid] = (counting.get(37, 0) + counting.get(39, 0)) / ip if ip else 0
        elif sid == 47:  # ERA
            result[sid] = (counting.get(45, 0) * 9) / ip if ip else 0
        elif sid == 38:  # OBA (opponent batting avg)
            tbf = counting.get(35, 0)
            result[sid] = counting.get(37, 0) / tbf if tbf else 0
        elif sid == 49:  # K/9
            result[sid] = (counting.get(48, 0) * 9) / ip if ip else 0
        elif sid == 82:  # K/BB
            p_bb = counting.get(39, 0)
            result[sid] = counting.get(48, 0) / p_bb if p_bb else 0
        else:
            # Counting stat — use directly
            result[sid] = counting.get(sid, 0)

    return result


class BoxScore(ABC):
    ''' '''
    def __init__(self, data):
        self.winner = data['winner']

        self._process_team(data['home'], True)

        if 'away' in data:
            self._process_team(data['away'], False)
        else:
            self._process_team(None, False)

    @abstractmethod
    def _process_team(self, team_data, is_home_team):
        team = {}

        if team_data is not None:
            team['id'] = team_data['teamId']

        if is_home_team:
            self.home_team = team['id']
        else:
            self.away_team = team.get('id')

    def __repr__(self):
        away_team = self.away_team or "BYE"
        home_team = self.home_team or "BYE"
        return f'Box Score({away_team} at {home_team})'


class H2HCategoryBoxScore(BoxScore):
    '''Boxscore class for head to head categories leagues'''
    def __init__(self, data, pro_schedule, year, scoring_period=0, scoring_items=None):
        # Parse scoring settings before _process_team runs
        self._scoring_cat_ids = set()
        self._reverse_cat_ids = set()
        for item in (scoring_items or []):
            sid = item.get('statId')
            if sid is not None:
                self._scoring_cat_ids.add(sid)
                if item.get('isReverseItem', False):
                    self._reverse_cat_ids.add(sid)

        # Store raw team data for roster-based recomputation
        self._raw_data = data
        super().__init__(data)

        # Recompute W-L-T from roster data when scoring items are available
        if self._scoring_cat_ids:
            self._recompute_from_rosters()

    def _process_team(self, team_data, is_home_team):
        super()._process_team(team_data, is_home_team)

        team = {}

        if team_data is not None:
            team['wins'] = team_data['cumulativeScore']['wins']
            team['losses'] = team_data['cumulativeScore']['losses']
            team['ties'] = team_data['cumulativeScore']['ties']

            team['stats'] = {}
            for stat_key, stat_dict in team_data['cumulativeScore']['scoreByStat'].items():
                team['stats'][STATS_MAP[int(stat_key)]] = {
                    'value': stat_dict['score'],
                    'result': stat_dict['result']
                }

        if is_home_team:
            self.home_wins = team['wins']
            self.home_losses = team['losses']
            self.home_ties = team['ties']
            self.home_stats = team['stats']
        else:
            self.away_wins = team.get('wins')
            self.away_losses = team.get('losses')
            self.away_ties = team.get('ties')
            self.away_stats = team.get('stats')

    def _recompute_from_rosters(self):
        """Recompute category stats and W-L-T from rosterForMatchupPeriod player data.

        ESPN's cumulativeScore can be stale/cached. The per-player stats in
        rosterForMatchupPeriod are accurate, so we aggregate them ourselves.
        """
        home_data = self._raw_data.get('home')
        away_data = self._raw_data.get('away')
        if not home_data or not away_data:
            return

        home_agg = _aggregate_roster_stats(home_data, self._scoring_cat_ids)
        away_agg = _aggregate_roster_stats(away_data, self._scoring_cat_ids)
        if home_agg is None or away_agg is None:
            return  # No roster data available, keep cumulativeScore values

        # Rebuild stats dicts and compute W-L-T
        home_stats = {}
        away_stats = {}
        home_w = home_l = home_t = 0

        for sid in self._scoring_cat_ids:
            hv = home_agg.get(sid, 0)
            av = away_agg.get(sid, 0)
            name = STATS_MAP.get(sid, f'stat_{sid}')
            reverse = sid in self._reverse_cat_ids

            if abs(hv - av) < 1e-9:
                h_result, a_result = 'TIE', 'TIE'
                home_t += 1
            elif (hv > av and not reverse) or (hv < av and reverse):
                h_result, a_result = 'WIN', 'LOSS'
                home_w += 1
            else:
                h_result, a_result = 'LOSS', 'WIN'
                home_l += 1

            home_stats[name] = {'value': hv, 'result': h_result}
            away_stats[name] = {'value': av, 'result': a_result}

        self.home_wins = home_w
        self.home_losses = home_l
        self.home_ties = home_t
        self.home_stats = home_stats

        self.away_wins = home_l  # away wins = home losses
        self.away_losses = home_w
        self.away_ties = home_t
        self.away_stats = away_stats

        # Clean up reference to raw data
        del self._raw_data


class H2HPointsBoxScore(BoxScore):
    '''Boxscore class for head to head points leagues'''
    def __init__(self, data, pro_schedule, year, scoring_period=0, scoring_items=None):
        super().__init__(data)

        (self.home_team, self.home_score, self.home_projected, self.home_lineup) = self._get_team_data('home', data, pro_schedule, scoring_period, year)

        (self.away_team, self.away_score, self.away_projected, self.away_lineup) = self._get_team_data('away', data, pro_schedule, scoring_period, year)

    def _process_team(self, team_data, is_home_team):
        super()._process_team(team_data, is_home_team)
        # TODO implement setting the scores

    def _get_team_data(self, team, data, pro_schedule, week, year):
      if team not in data:
        return (0, 0, -1, [])

      team_id = data[team]['teamId']
      team_projected = -1
      if 'totalPointsLive' in data[team]:
        team_score = round(data[team]['totalPointsLive'], 2)
        team_projected = round(data[team].get('totalProjectedPointsLive', -1), 2)
      else:
        team_score = round(data[team]['totalPoints'], 2)
      team_roster = data[team].get('rosterForCurrentScoringPeriod', {}).get('entries', [])
      team_lineup = [BoxPlayer(player, pro_schedule, week, year) for player in team_roster]

      return (team_id, team_score, team_projected, team_lineup)
