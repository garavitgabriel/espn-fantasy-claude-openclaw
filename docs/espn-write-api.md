# ESPN Write API Stub

**UNVERIFIED — pending Phase 0 browser capture**

This document records the current write-endpoint hypotheses from the delegation brief.
Nothing here has been confirmed against live ESPN browser traffic yet.
Do not trust these payloads for production writes until Phase 0 capture is complete.

## Hypothesized write host

- Host: `https://lm-api-writes.fantasy.espn.com`
- Base path: `/apis/v3/games/flb/seasons/{year}/segments/0/leagues/{leagueId}`
- Transactions endpoint: `POST /transactions/`

## Hypothesized auth / headers

- Cookies:
  - `espn_s2=<...>`
  - `SWID={<...>}`
- Headers:
  - `Content-Type: application/json`
  - `x-fantasy-source: kona`
  - `x-fantasy-platform: <TBD from browser capture>`

## Hypothesized lineup payload

```json
{
  "isLeagueManager": false,
  "teamId": 1,
  "type": "ROSTER",
  "scoringPeriodId": 73,
  "executionType": "EXECUTE",
  "items": [
    {
      "playerId": 12345,
      "type": "LINEUP",
      "fromLineupSlotId": 16,
      "toLineupSlotId": 5
    }
  ]
}
```

## Hypothesized add/drop payload

```json
{
  "isLeagueManager": false,
  "teamId": 1,
  "type": "FREEAGENT",
  "executionType": "EXECUTE",
  "items": [
    { "type": "ADD", "playerId": 12345 },
    { "type": "DROP", "playerId": 67890 }
  ]
}
```

Possible variant: `type: "WAIVER"`.

## Hypothesized trade proposal payload

```json
{
  "isLeagueManager": false,
  "teamId": 1,
  "type": "TRADE_PROPOSAL",
  "executionType": "EXECUTE",
  "tradePartnerTeamId": 2,
  "items": [
    { "type": "TRADE_GIVE", "playerId": 111 },
    { "type": "TRADE_RECEIVE", "playerId": 222 }
  ]
}
```

## Hypothesized trade accept payload

```json
{
  "isLeagueManager": false,
  "teamId": 1,
  "type": "TRADE_ACCEPT",
  "executionType": "EXECUTE",
  "proposalId": 999,
  "items": []
}
```

## Phase 0 capture checklist

Capture and replace every hypothesis above with real browser-observed values:

1. Exact method + URL for lineup swap
2. Exact method + URL for add/drop
3. Exact method + URL for trade propose
4. Required headers beyond cookies
5. Exact response shape for success and rejection
6. Any anti-CSRF tokens or platform/version headers
7. Whether trade accept uses the same endpoint or another path

## Safety note

Current repo defaults remain:

- `DRY_RUN=true`
- `WRITES_ENABLED=false`

So this scaffold cannot perform live writes until Gabriel explicitly completes Phase 0 and later flips config intentionally.
