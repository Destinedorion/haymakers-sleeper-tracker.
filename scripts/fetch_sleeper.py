#!/usr/bin/env python3
"""Fetch public Sleeper league data. No authentication or third-party packages required."""
import datetime as dt
import json
import os
import pathlib
import urllib.request

LEAGUE_ID = "1312078538953723904"
BASE = "https://api.sleeper.app/v1"
OUT = pathlib.Path("data/latest.json")

def get(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "HaymakersSleeperTracker/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)

def main():
    league = get(f"/league/{LEAGUE_ID}")
    if not isinstance(league, dict) or str(league.get("league_id")) != LEAGUE_ID:
        raise RuntimeError("Sleeper league ID did not match")
    rosters = get(f"/league/{LEAGUE_ID}/rosters")
    users = get(f"/league/{LEAGUE_ID}/users")
    nfl_state = get("/state/nfl")
    week = int(nfl_state.get("week") or 1)
    weeks = sorted(set([max(1, week-1), week, min(18, week+1)]))
    matchups = {str(w): get(f"/league/{LEAGUE_ID}/matchups/{w}") for w in weeks}
    transactions = {str(w): get(f"/league/{LEAGUE_ID}/transactions/{w}") for w in weeks}
    traded_picks = get(f"/league/{LEAGUE_ID}/traded_picks")
    user_by_id = {str(u.get("user_id")): u for u in users}
    haymakers = []
    for roster in rosters:
        user = user_by_id.get(str(roster.get("owner_id")), {})
        names = [user.get("display_name", ""), user.get("metadata", {}).get("team_name", ""), roster.get("metadata", {}).get("team_name", "")]
        if any("haymaker" in str(name).lower() for name in names):
            haymakers.append({"roster_id": roster.get("roster_id"), "owner_id": roster.get("owner_id"), "names": names})
    # The NFL player directory permits accurate player-ID-to-name lookup and unowned-player checks.
    players = get("/players/nfl")
    owned = {str(pid) for roster in rosters for pid in (roster.get("players") or [])}
    eligible = {}
    for pid, p in players.items():
        if not isinstance(p, dict) or p.get("position") not in ("QB", "RB", "WR", "TE", "DEF"):
            continue
        if not p.get("active") and pid not in owned:
            continue
        eligible[pid] = {
            "name": p.get("full_name") or p.get("first_name", "") + " " + p.get("last_name", ""),
            "position": p.get("position"), "team": p.get("team"), "age": p.get("age"),
            "injury_status": p.get("injury_status"), "status": p.get("status"),
            "owned": pid in owned
        }
    snapshot = {
        "fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "league_id": LEAGUE_ID, "league": league, "nfl_state": nfl_state,
        "users": users, "rosters": rosters, "haymakers_matches": haymakers,
        "matchups": matchups, "transactions": transactions, "traded_picks": traded_picks,
        "players": eligible,
        "notes": "Player injury fields are Sleeper metadata, not a substitute for official practice reports. Available means not rostered in this league, not necessarily waiver-claimable right now."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {OUT}: {len(rosters)} rosters, {len(users)} users, {len(eligible)} eligible players; Haymakers matches: {haymakers}")

if __name__ == "__main__":
    main()
