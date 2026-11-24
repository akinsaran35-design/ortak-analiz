import json
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

LEAGUES = {"İngiltere Championship": "soccer_efl_champ", "İngiltere Premier Lig": "soccer_epl",
           "Almanya Bundesliga": "soccer_germany_bundesliga", "Fransa Ligue 1": "soccer_france_ligue_one",
           "İspanya La Liga": "soccer_spain_la_liga", "İtalya Serie A": "soccer_italy_serie_a"}
def normalize(name):
    name = unicodedata.normalize("NFKD", name.casefold())
    name = "".join(c for c in name if not unicodedata.combining(c))
    return " ".join(t for t in re.findall(r"[a-z0-9]+", name) if t not in {"fc", "cf", "afc", "sc"})
def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
def main():
    daily = json.loads(Path("daily.json").read_text(encoding="utf-8"))
    odds = json.loads(Path("odds.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    matched, unmatched = [], []
    for candidate in daily.get("candidates", []):
        league = LEAGUES.get(candidate.get("league"))
        teams = candidate.get("match", "").split(" – ")
        matches = []
        if league and len(teams) == 2:
            for event in odds.get("events", []):
                kickoff = parse_time(event["kickoff"])
                if (event["league"] == league and kickoff > now
                    and kickoff.astimezone(ZoneInfo("Europe/Istanbul")).date().isoformat() == candidate["date"]
                    and normalize(event["home"]) == normalize(teams[0])
                    and normalize(event["away"]) == normalize(teams[1])):
                    matches.append(event)
        if len(matches) != 1:
            unmatched.append({"match": candidate.get("match"), "reason": "ambiguous" if matches else "no_exact_match"})
            continue
        event = matches[0]
        fresh = 0
        for book in event.get("bookmakers", []):
            for line in book.get("lines", []):
                try:
                    age = now - parse_time(line["lastUpdate"])
                    if timedelta(0) <= age <= timedelta(minutes=30):
                        fresh += 1
                except (ValueError, TypeError, KeyError, AttributeError):
                    pass
        matched.append({"match": candidate["match"], "eventId": event["id"], "kickoff": event["kickoff"], "freshLineCount": fresh})
    report = {"version": "2.7", "updatedAt": now.isoformat(), "decision": "PAS",
              "matchedCount": len(matched), "unmatchedCount": len(unmatched),
              "matched": matched, "unmatched": unmatched, "modelCalibrated": False}
    Path("matching.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Matched:", len(matched), "Unmatched:", len(unmatched))
if __name__ == "__main__":
    main()
