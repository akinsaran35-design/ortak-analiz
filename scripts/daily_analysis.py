"""Ortak Analiz V1.4 — transparent fixtures diagnostic, safe PAS.
Free community fixture data; no claims of live odds or verified kickoffs.
"""
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TR = timezone(timedelta(hours=3))
now = datetime.now(TR)
today = now.date()
year = today.year if today.month >= 7 else today.year - 1
season = f"{year}-{str(year + 1)[-2:]}"
LEAGUES = {
    "İngiltere Premier Lig": "en.1",
    "İngiltere Championship": "en.2",
    "Almanya Bundesliga": "de.1",
    "İspanya La Liga": "es.1",
    "İtalya Serie A": "it.1",
    "Fransa Ligue 1": "fr.1",
}
BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"
report = {
    "date": today.isoformat(), "decision": "PAS", "picks": [],
    "updatedAt": now.isoformat(timespec="seconds"),
    "source": "https://github.com/openfootball/football.json",
    "method": "Açık fikstür taraması; oran ve olasılık doğrulaması yapılmadı.",
    "version": "1.4", "leaguesChecked": 0, "leaguesLoaded": 0,
    "fixturesToday": 0, "fixturesNext7Days": 0,
    "leagueDiagnostics": [], "upcoming": [],
}

def match_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None

def get_matches(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("matches"), list):
        return payload["matches"]
    matches = []
    for round_data in payload.get("rounds", []):
        if isinstance(round_data, dict) and isinstance(round_data.get("matches"), list):
            matches.extend(round_data["matches"])
    return matches

def team_name(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("name") or value.get("code") or ""
    return ""

for league, code in LEAGUES.items():
    report["leaguesChecked"] += 1
    url = f"{BASE}/{season}/{code}.json"
    diag = {"league": league, "status": "unavailable", "today": 0, "next7": 0}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "OrtakAnaliz/1.4"})
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read(3_000_000).decode("utf-8"))
        matches = get_matches(payload)
        diag["status"] = "ok" if matches else "empty"
        diag["matchesInFile"] = len(matches)
        report["leaguesLoaded"] += 1
        for match in matches:
            if not isinstance(match, dict):
                continue
            d = match_date(match.get("date") or match.get("datetime"))
            home = team_name(match.get("team1") or match.get("home") or match.get("homeTeam"))
            away = team_name(match.get("team2") or match.get("away") or match.get("awayTeam"))
            if not d or not home or not away:
                continue
            if d == today:
                diag["today"] += 1
                report["fixturesToday"] += 1
            if today <= d <= today + timedelta(days=7):
                diag["next7"] += 1
                report["fixturesNext7Days"] += 1
                if len(report["upcoming"]) < 25:
                    report["upcoming"].append({"date": d.isoformat(), "league": league,
                                               "match": f"{home} – {away}"})
    except Exception as exc:
        diag["error"] = f"{type(exc).__name__}: {str(exc)[:110]}"
    report["leagueDiagnostics"].append(diag)

report["upcoming"].sort(key=lambda x: (x["date"], x["league"], x["match"]))
report["reason"] = (
    f"{report['leaguesLoaded']}/{report['leaguesChecked']} lig kaynağı okundu. "
    f"Bugün {report['fixturesToday']}, önümüzdeki 7 günde "
    f"{report['fixturesNext7Days']} fikstür satırı bulundu. "
    "Başlama saatleri ve güncel uluslararası bahis oranları doğrulanmadığı "
    "için otomatik seçim yapılmadı. Kaynak verisi eksik veya eski olabilir."
)
Path("daily.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(report["reason"])
for diag in report["leagueDiagnostics"]:
    print(diag)
