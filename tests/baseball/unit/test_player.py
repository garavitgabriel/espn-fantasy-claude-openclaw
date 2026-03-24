import sys
import types
from unittest import TestCase

sys.modules.setdefault('requests', types.SimpleNamespace(get=None, post=None))

from espn_api.baseball.player import Player
from mcp_server.formatters import fmt_free_agents


class TestPlayer(TestCase):

    def test_free_agent_wrapper_prefers_nested_pitcher_position(self):
        player = Player({
            'defaultPositionId': 1,
            'playerPoolEntry': {
                'player': {
                    'id': 123,
                    'fullName': 'Joe Musgrove',
                    'defaultPositionId': 14,
                    'eligibleSlots': [13, 14, 15, 16, 17],
                    'proTeamId': 25,
                    'injuryStatus': 'ACTIVE',
                    'ownership': {'percentOwned': 87.4, 'percentStarted': 71.2},
                    'stats': [],
                }
            },
            'status': 'FREEAGENT',
        }, 2026)

        self.assertEqual(player.position, 'SP/RP')
        self.assertEqual(player.eligibleSlots, ['P', 'SP', 'RP', 'BE', 'IL'])

    def test_player_wrapper_ignores_junk_slots_for_display_position(self):
        player = Player({
            'defaultPositionId': 1,
            'player': {
                'id': 456,
                'fullName': 'Utility Infielder',
                'defaultPositionId': 5,
                'eligibleSlots': [12, 19, 4, 16],
                'proTeamId': 10,
                'injuryStatus': 'ACTIVE',
                'ownership': {},
                'stats': [],
            },
            'status': 'FREEAGENT',
        }, 2026)

        self.assertEqual(player.position, 'SS')
        self.assertEqual(player.eligibleSlots, ['UTIL', 'IF', 'SS', 'BE'])

    def test_free_agent_formatter_uses_improved_position_label(self):
        player = Player({
            'defaultPositionId': 1,
            'playerPoolEntry': {
                'player': {
                    'id': 789,
                    'fullName': 'Joe Musgrove',
                    'defaultPositionId': 14,
                    'eligibleSlots': [13, 14, 15],
                    'proTeamId': 25,
                    'injuryStatus': 'ACTIVE',
                    'ownership': {'percentOwned': 87.4, 'percentStarted': 71.2},
                    'stats': [],
                }
            },
            'status': 'FREEAGENT',
        }, 2026)

        rendered = fmt_free_agents([player])

        self.assertIn('| Joe Musgrove | SP/RP | SD | 0 | 87.4% | 71.2% |', rendered)
