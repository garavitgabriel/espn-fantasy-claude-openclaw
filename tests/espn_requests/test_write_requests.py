from unittest import TestCase
from unittest.mock import Mock, patch

from espn_api.baseball import League
from espn_api.requests.espn_requests import EspnFantasyRequests


class TestWriteRequests(TestCase):
    @patch("espn_api.requests.espn_requests.requests.post")
    def test_write_post_uses_write_endpoint_and_headers(self, mock_post):
        mock_response = Mock(status_code=200)
        mock_response.content = b'{"ok": true}'
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        req = EspnFantasyRequests(
            sport="mlb",
            year=2026,
            league_id=612122596,
            cookies={"espn_s2": "s2", "SWID": "{swid}"},
        )
        payload = {"type": "ROSTER"}
        result = req.write_post(payload)

        self.assertEqual(result, {"ok": True})
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("lm-api-writes.fantasy.espn.com", args[0])
        self.assertEqual(kwargs["json"], payload)
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["headers"]["x-fantasy-source"], "kona")

    def test_league_write_methods_delegate_to_request_layer(self):
        league = League(league_id=1, year=2026, fetch_league=False)
        league.espn_request = Mock()
        league.espn_request.write_post.return_value = {"ok": True}

        lineup = league.set_lineup(1, 55, [{"playerId": 9, "type": "LINEUP"}])
        add_drop = league.add_drop_player(1, 100, 200)
        trade = league.propose_trade(1, 2, [100], [200])
        accept = league.accept_trade(1, 999)

        self.assertEqual(lineup, {"ok": True})
        self.assertEqual(add_drop, {"ok": True})
        self.assertEqual(trade, {"ok": True})
        self.assertEqual(accept, {"ok": True})
        self.assertEqual(league.espn_request.write_post.call_count, 4)
