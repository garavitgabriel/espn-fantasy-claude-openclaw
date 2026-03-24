import json
import sys
import types
from unittest import TestCase, mock

sys.modules.setdefault('requests', types.SimpleNamespace(get=None, post=None))

from espn_api.baseball import League
from espn_api.baseball.constant import get_position_filter_slot_ids


class TestLeagueFreeAgents(TestCase):

    def test_position_filter_slot_lookup_supports_expected_labels(self):
        self.assertEqual(get_position_filter_slot_ids('SP'), [14])
        self.assertEqual(get_position_filter_slot_ids('of'), [5])
        self.assertEqual(get_position_filter_slot_ids(' UT '), [12])
        self.assertEqual(get_position_filter_slot_ids('missing'), [])

    def test_free_agents_passes_sp_slot_filter(self):
        league = League(1, 2026, fetch_league=False)
        league.espn_request.league_get = mock.Mock(return_value={'players': []})

        league.free_agents(week=1, position='SP')

        headers = league.espn_request.league_get.call_args.kwargs['headers']
        filters = json.loads(headers['x-fantasy-filter'])

        self.assertEqual(filters['players']['filterSlotIds']['value'], [14])

    def test_free_agents_passes_of_slot_filter(self):
        league = League(1, 2026, fetch_league=False)
        league.espn_request.league_get = mock.Mock(return_value={'players': []})

        league.free_agents(week=1, position='OF')

        headers = league.espn_request.league_get.call_args.kwargs['headers']
        filters = json.loads(headers['x-fantasy-filter'])

        self.assertEqual(filters['players']['filterSlotIds']['value'], [5])

    def test_free_agents_keeps_empty_slot_filter_when_position_not_set(self):
        league = League(1, 2026, fetch_league=False)
        league.espn_request.league_get = mock.Mock(return_value={'players': []})

        league.free_agents(week=1)

        headers = league.espn_request.league_get.call_args.kwargs['headers']
        filters = json.loads(headers['x-fantasy-filter'])

        self.assertEqual(filters['players']['filterSlotIds']['value'], [])
