"""Ortak Analiz V1.6 — transparent historical football model diagnostics.
OpenFootball community data; statistical candidates are NOT betting selections.
"""
import json
import math
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TR = timezone(timedelta(hours=3))
now = datetime.now(TR)
today = now.date()
year = today.year if today.month >= 7 else today.year - 1
seasons = [f"{y}-{str(y+1)[-2:]}" for y in (year, year-1)]
from league_config import FIXTURE_CODES as LEAGUES
BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"


def parse_date(value):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def team_name(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("name") or value.get("code") or "").strip()
    return ""


from fixture_schema import matches_in
from football_form import form
import football_history_cache as history_cache

def final_score(match):
    score = match.get("score")
    if not isinstance(score, dict):
        return None
    # Check keys for presence, not truthiness: 0-0 is a valid result.
    for key in ("ft", "fulltime", "fullTime"):
        if key not in score or score[key] is None:
            continue
        value = score[key]
        if isinstance(value, list) and len(value) == 2 and all(type(n) is int and n >= 0 for n in value):
            return tuple(value)
        if isinstance(value, dict):
            home, away = value.get("home"), value.get("away")
            if type(home) is int and type(away) is int and home >= 0 and away >= 0:
                return home, away
    return None


def fetch(season, code):
    if code == "tr.1":
        from turkey_source import fetch as turkey_fetch
        return turkey_fetch(season)
    url = f"{BASE}/{season}/{code}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "OrtakAnaliz/1.6"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return matches_in(json.loads(response.read(4_000_000).decode("utf-8")))


def recent_stats(history, team, home_only):
    selected = []
    for d, home, away, hg, ag in history:
        if home_only and home == team:
            selected.append((d, hg, ag))
        elif not home_only and away == team:
            selected.append((d, ag, hg))
    selected.sort(key=lambda item: item[0], reverse=True)
    # Prefer home/away data, but transparently fall back to all venues.
    venue_count = len(selected)
    if venue_count < 5:
        selected = []
        for d, home, away, hg, ag in history:
            if home == team:
                selected.append((d, hg, ag))
            elif away == team:
                selected.append((d, ag, hg))
        selected.sort(key=lambda item: item[0], reverse=True)
        mode = "all_venues_fallback"
    else:
        mode = "venue_specific"
    recent = selected[:10]
    if len(recent) < 5:
        return None, {"availableVenue": venue_count, "availableAll": len(selected)}
    return {
        "n": len(recent), "gf": sum(x[1] for x in recent) / len(recent),
        "ga": sum(x[2] for x in recent) / len(recent), "mode": mode,
        "venueMatchesAvailable": venue_count,
    }, None


def over_probability(expected, threshold):
    return 1 - sum(math.exp(-expected) * expected ** k / math.factorial(k)
                   for k in range(threshold + 1))


def percentage(probability):
    return round(100 * min(1, max(0, probability)), 1)


report = {
    "date": today.isoformat(), "decision": "PAS", "picks": [],
    "version": "1.6", "updatedAt": now.isoformat(timespec="seconds"),
    "source": "https://github.com/openfootball/football.json",
    "additionalSources": {"tr.1": {"results": "https://football-data.co.uk/turkeym.php", "fixtures": "The Odds API UK snapshot or independent ESPN scheduled fixtures; incomplete coverage possible"}},
    "method": "Son 10 maç; önce iç/dış saha, eksikse tüm sahalar; basit Poisson. Kalibrasyon yok.",
    "leaguesChecked": len(LEAGUES), "leaguesLoaded": 0,
    "fixturesToday": 0, "fixturesNext7Days": 0,
    "leagueDiagnostics": [], "upcoming": [], "candidates": [], "candidateCount": 0,
    "fixtureWindowDays": 7, "upcomingCount": 0, "upcomingCountsByDate": {},
    "dataQuality": {"verifiedOdds": False, "verifiedKickoffTimes": False,
                    "modelCalibrated": False, "bettingRecommendation": False},
}

history_archive=history_cache.read()
for league, code in LEAGUES.items():
    diagnostic = {"league": league, "status": "unavailable", "today": 0,
                  "next7": 0, "completedMatches": 0, "candidates": 0,
                  "excluded": {"alreadyScored": 0, "insufficientHistory": 0},
                  "seasonsLoaded": [], "seasonErrors": {}, "cachedHistoricalSeasons": {}}
    all_matches = []
    for season in seasons:
        try:
            matches = fetch(season, code)
            all_matches.extend(matches)
            diagnostic["seasonsLoaded"].append(season)
            history_cache.remember(history_archive,code,season,matches,now)
        except Exception as exc:
            diagnostic["seasonErrors"][season] = f"{type(exc).__name__}: {str(exc)[:90]}"
            cached,stamp=history_cache.recover(history_archive,code,season,now)
            if cached:
                all_matches.extend(cached)
                diagnostic["cachedHistoricalSeasons"][season]=stamp
    if not diagnostic["seasonsLoaded"] and not diagnostic["cachedHistoricalSeasons"]:
        report["leagueDiagnostics"].append(diagnostic)
        continue
    if diagnostic["seasonsLoaded"]:report["leaguesLoaded"] += 1
    diagnostic["status"] = "ok" if len(diagnostic["seasonsLoaded"]) == len(seasons) else "partial"
    history = []
    form_history = []
    fixtures = []
    seen = set()
    for match in all_matches:
        if not isinstance(match, dict):
            continue
        d = parse_date(match.get("date") or match.get("datetime"))
        home = team_name(match.get("team1") or match.get("home") or match.get("homeTeam"))
        away = team_name(match.get("team2") or match.get("away") or match.get("awayTeam"))
        if not d or not home or not away:
            continue
        identity = (d, home, away)
        score = final_score(match)
        if d < today and score is not None:
            form_history.append((d, home, away, score[0], score[1]))
        if identity in seen:
            continue
        seen.add(identity)
        score = final_score(match)
        if d < today and score is not None:
            history.append((d, home, away, score[0], score[1]))
        if today <= d <= today + timedelta(days=7):
            fixtures.append((d, home, away, score))
            diagnostic["next7"] += 1
            report["fixturesNext7Days"] += 1
            if d == today:
                diagnostic["today"] += 1
                report["fixturesToday"] += 1
    if code == "tr.1":
        sources=sorted({m.get("fixtureSource") for m in all_matches if isinstance(m,dict) and m.get("fixtureSource") in ("ESPN","The Odds API")})
        diagnostic["fixtureSources"]=sources
        diagnostic["fixtureScope"]="independent_espn_fallback" if "ESPN" in sources else "fresh_odds_events_only" if sources else "unavailable"
        diagnostic["status"] = "partial"
    diagnostic["completedMatches"] = len(history)
    history_through = max((r[0] for r in history), default=None)
    for d, home, away, score in fixtures:
        if score is not None:
            diagnostic["excluded"]["alreadyScored"] += 1
            continue
        report["upcoming"].append({"date": d.isoformat(), "league": league,
                                    "match": f"{home} – {away}",
                                    "formResearch": form(form_history,home,away,today)})
        home_stats, home_error = recent_stats(history, home, True)
        away_stats, away_error = recent_stats(history, away, False)
        if home_error or away_error:
            diagnostic["excluded"]["insufficientHistory"] += 1
            continue
        home_expected = max(0.15, min(4.0, (home_stats["gf"] + away_stats["ga"]) / 2))
        away_expected = max(0.15, min(4.0, (away_stats["gf"] + home_stats["ga"]) / 2))
        markets = {
            "1.5 Üst": percentage(over_probability(home_expected + away_expected, 1)),
            "2.5 Üst": percentage(over_probability(home_expected + away_expected, 2)),
            "KG Var": percentage((1 - math.exp(-home_expected)) * (1 - math.exp(-away_expected))),
        }
        report["candidates"].append({
            "date": d.isoformat(), "league": league, "match": f"{home} – {away}",
            "markets": markets, "historyThrough": history_through.isoformat() if history_through else None, "sample": {"home": home_stats["n"], "away": away_stats["n"]},
            "sampleMode": {"home": home_stats["mode"], "away": away_stats["mode"]},
            "expectedGoals": {"home": round(home_expected, 2), "away": round(away_expected, 2)},
            "historyCacheUsed": bool(diagnostic["cachedHistoricalSeasons"]),
            "historyCachedSeasons": dict(diagnostic["cachedHistoricalSeasons"]),
            "status": "Kalibre edilmemiş istatistiksel aday; geçmiş veri yedeği kullanıldı; bahis önerisi değil" if diagnostic["cachedHistoricalSeasons"] else "Kalibre edilmemiş istatistiksel aday; bahis önerisi değil",
            "odds": None, "edge": None,
        })
        diagnostic["candidates"] += 1
    report["leagueDiagnostics"].append(diagnostic)

report["upcoming"].sort(key=lambda item: (item["date"], item["league"], item["match"]))
report["upcomingCount"] = len(report["upcoming"])
for fixture in report["upcoming"]:
    day = fixture["date"]
    report["upcomingCountsByDate"][day] = report["upcomingCountsByDate"].get(day, 0) + 1
report["fixtureCoverageComplete"] = all(d["status"] == "ok" for d in report["leagueDiagnostics"])
report["candidateListLimit"] = None
report["candidates"].sort(key=lambda item: (item["date"], -item["markets"]["1.5 Üst"], item["match"]))
report["candidateCount"] = len(report["candidates"])
report["candidateListComplete"] = True
report["reason"] = (
    f"PAS — {report['leaguesLoaded']}/{report['leaguesChecked']} lig okundu; "
    f"bugün {report['fixturesToday']}, 7 günde {report['fixturesNext7Days']} fikstür; "
    f"{report['candidateCount']} istatistiksel aday. "
    "Güncel oranlar, maç başlama saatleri ve model kalibrasyonu doğrulanmadığından "
    "otomatik bahis seçimi yapılmadı."
)
report["forecastTimingVersion"] = "6.82"
report["historyCutoffExclusive"] = today.isoformat()
report["generationCompletedAt"] = datetime.now(TR).isoformat()
history_cache.write(history_archive,now,LEAGUES.values(),seasons)
Path("daily.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(report["reason"])
for diagnostic in report["leagueDiagnostics"]:
    print(json.dumps(diagnostic, ensure_ascii=False))
