import json
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

from league_config import ODDS_CODES as LEAGUES
def normalize(name):
    name = unicodedata.normalize("NFKD", name.casefold().replace("&", " and "))
    name = "".join(c for c in name if not unicodedata.combining(c))
    return " ".join(t for t in re.findall(r"[a-z0-9]+", name) if t not in {"fc", "cf", "afc", "sc"})
ALIASES = {
    "soccer_germany_bundesliga": {
        "sv werder bremen": "werder bremen",
        "bayern munchen": "bayern munich",
        "1 fsv mainz 05": "fsv mainz 05",
        "1 union berlin": "union berlin",
    },
    "soccer_france_ligue_one": {
        "stade brestois 29": "brest",
        "le havre ac": "le havre",
        "rc strasbourg alsace": "strasbourg",
    },
}
# Explicit aliases observed in the two published data feeds; no fuzzy matching.
for _league, _aliases in {
    "soccer_netherlands_eredivisie": {
        "willem ii tilburg": "willem ii",
        "psv": "psv eindhoven",
        "cambuur leeuwarden": "cambuur",
        "sbv excelsior": "excelsior",
        "telstar 1963": "telstar",
        "nec": "nec nijmegen",
        "twente 65": "twente enschede",
        "feyenoord rotterdam": "feyenoord",
        "pec zwolle": "zwolle",
        "az": "az alkmaar"
    },
    "soccer_portugal_primeira_liga": {
        "cd nacional": "nacional",
        "vitoria guimaraes": "vitoria",
        "vitoria sc": "vitoria",
        "estrela da amadora": "estrela",
        "cd santa clara": "santa clara",
        "sporting clube de portugal": "sporting lisbon",
        "gd estoril praia": "estoril",
        "sport lisboa e benfica": "benfica",
        "casa pia ac": "casa pia",
        "sporting clube de braga": "braga"
    },
    "soccer_france_ligue_one": {
        "lille osc": "lille",
        "angers sco": "angers",
        "racing club de lens": "rc lens",
        "olympique lyonnais": "lyon",
        "stade rennais 1901": "rennes",
        "aj auxerre": "auxerre",
        "olympique de marseille": "marseille"
    },
    "soccer_spain_la_liga": {
        "levante ud": "levante",
        "deportivo alaves": "alaves",
        "club atletico de madrid": "atletico madrid",
        "real sociedad de futbol": "real sociedad",
        "rc celta de vigo": "celta vigo",
        "rc deportivo la coruna": "deportivo la coruna",
        "athletic club": "athletic bilbao",
        "real betis balompie": "real betis",
        "rayo vallecano de madrid": "rayo vallecano",
        "rcd espanyol de barcelona": "espanyol"
    },
    "soccer_italy_serie_a": {
        "ac monza": "monza",
        "como 1907": "como",
        "internazionale milano": "inter milan",
        "genoa cfc": "genoa",
        "us sassuolo calcio": "sassuolo",
        "ssc napoli": "napoli",
        "venezia": "venezia",
        "bologna 1909": "bologna",
        "us lecce": "lecce",
        "ss lazio": "lazio",
        "udinese calcio": "udinese",
        "acf fiorentina": "fiorentina",
        "frosinone calcio": "frosinone",
        "parma calcio 1913": "parma",
        "cagliari calcio": "cagliari"
    },
    "soccer_epl": {
        "brighton hove albion": "brighton and hove albion"
    },
    "soccer_germany_bundesliga": {
        "bayer 04 leverkusen": "bayer leverkusen",
        "tsg 1899 hoffenheim": "tsg hoffenheim"
    }
}.items():
    ALIASES.setdefault(_league, {}).update(_aliases)

def canonical(name, league):
    if league == "soccer_turkey_super_league":
        from turkey_source import team_key
        return team_key(name)
    normalized = normalize(name)
    return ALIASES.get(league, {}).get(normalized, normalized)

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
        other_dates = []
        if league and len(teams) == 2:
            for event in odds.get("events", []):
                kickoff = parse_time(event["kickoff"])
                if (event["league"] == league and kickoff > now
                    and canonical(event["home"], league) == canonical(teams[0], league)
                    and canonical(event["away"], league) == canonical(teams[1], league)):
                    event_date = kickoff.astimezone(ZoneInfo("Europe/Istanbul")).date().isoformat()
                    if event_date == candidate["date"]:
                        matches.append(event)
                    else:
                        other_dates.append(event_date)
        if len(matches) != 1:
            unmatched.append({"match": candidate.get("match"), "league": candidate.get("league"), "date": candidate.get("date"),
                              "reason": "ambiguous" if matches else "date_mismatch" if other_dates else "no_exact_match",
                              "providerDates": sorted(set(other_dates))})
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
    report = {"version": "2.8", "updatedAt": now.isoformat(), "decision": "PAS",
              "matchedCount": len(matched), "unmatchedCount": len(unmatched),
              "matched": matched, "unmatched": unmatched, "modelCalibrated": False}
    Path("matching.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Matched:", len(matched), "Unmatched:", len(unmatched))
if __name__ == "__main__":
    main()
