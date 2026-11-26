# Ortak Analiz V4.4 - Prospective validation
import json
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

from backtest import LEAGUES, fetch, team, predict, weighted_predict
from prospective_markets import capture, summarize

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime.now(timezone(timedelta(hours=3)))
TODAY = NOW.date()
ARCHIVE = ROOT / "prospective_archive.json"

records = json.loads(
    ARCHIVE.read_text(encoding="utf-8")
) if ARCHIVE.exists() else {}

from calendar_duplicate_guard import load_guard
blocked = load_guard(ROOT, records, "prospective", NOW)
calendar_duplicate_prevented = 0
errors = []

year = TODAY.year if TODAY.month >= 7 else TODAY.year - 1
years = {year - 1, year}

for r in records.values():
    if r["result"] is None:
        d = date.fromisoformat(r["date"])
        years.add(d.year if d.month >= 7 else d.year - 1)

seasons = [
    f"{y}-{str(y+1)[-2:]}"
    for y in sorted(years)
]

for league in LEAGUES:
    fixtures = {}
    failed = False

    for season in seasons:
        try:
            for m in fetch(season, league):
                try:
                    d = date.fromisoformat(m["date"][:10])
                    h = team(m.get("team1"))
                    a = team(m.get("team2"))
                    ft = (m.get("score") or {}).get("ft")

                    if not h or not a:
                        continue

                    valid = (
                        isinstance(ft, list)
                        and len(ft) == 2
                        and all(type(x) is int and x >= 0 for x in ft)
                    )

                    fixtures[(d, h, a)] = ft if valid else None

                except (ValueError, TypeError, KeyError, AttributeError):
                    continue

        except Exception as exc:
            errors.append(f"{league}/{season}: {exc}")
            failed = True

    if failed:
        continue

    history = sorted(
        (d, h, a, ft[0], ft[1])
        for (d, h, a), ft in fixtures.items()
        if d < TODAY and ft is not None
    )

    for (d, h, a), ft in sorted(fixtures.items()):
        key = json.dumps(
            [d.isoformat(), league, h, a],
            ensure_ascii=False
        )

        if key in records:
            # New outcomes are written only through verified_results below.
            continue

        if d <= TODAY or ft is not None:
            continue

        if d > TODAY + timedelta(days=7):
            continue

        if (league,h,a,d.isoformat()) in blocked:
            calendar_duplicate_prevented += 1
            continue

        old = predict(history, h, a)
        new = weighted_predict(history, h, a)

        if old is None or new is None or not history:
            continue

        baseline = sum(
            int(x[3] + x[4] >= 3)
            for x in history
        ) / len(history)

        try:
            market_forecasts = capture(history,old,new)
        except (ValueError,TypeError,ArithmeticError) as exc:
            errors.append(f"{league}/{d}/{h}/{a}: invalid prospective forecast ({type(exc).__name__})")
            continue

        records[key] = {
            "date": d.isoformat(),
            "league": league,
            "home": h,
            "away": a,
            "recordedAt": NOW.isoformat(),
            "modelVersion": "4.4",
            "old": old[1],
            "candidate": new[1],
            "baseline": baseline,
            "prospectiveMarkets": market_forecasts,
            "result": None
        }

from verified_results import load_verified, settle_verified
try:
    verified_count = settle_verified(records, load_verified(ROOT,NOW), NOW)
except (OSError, ValueError, KeyError, TypeError) as exc:
    verified_count = 0
    errors.append(f"verified_results: {exc}")

settled = [
    r for r in records.values()
    if r["result"] is not None
]

n = len(settled)

report = {
    "version": "4.4",
    "market": "2.5 Ust",
    "candidate": "weightedBrier",
    "updatedAt": NOW.isoformat(),
    "recorded": len(records),
    "verifiedFallbackSettled": verified_count,
    "calendarDuplicatePrevented": calendar_duplicate_prevented,
    "tested": n,
    "pending": len(records) - n,
    "minimumMatches": 500,
    "liveEnabled": False,
    "status": "collecting_data",
    "errors": errors,
    "marketResearchVersion": "4.85",
    "marketResearch": summarize(records,NOW)
}

if n:
    scores = {
        k: sum(
            (r[k] - int(sum(r["result"]) >= 3)) ** 2
            for r in settled
        ) / n
        for k in ("old", "candidate", "baseline")
    }

    report["scores"] = scores
    report["improvement"] = (
        scores["baseline"] - scores["candidate"]
    )

    if n >= 500 and not errors and all(x["invalid"]==0 for x in report["marketResearch"].values()):
        eligible = (
            scores["candidate"] < scores["old"]
            and report["improvement"] >= 0.001
        )

        report["status"] = (
            "review_required"
            if eligible else "not_qualified"
        )

ARCHIVE.write_text(
    json.dumps(records, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

(ROOT / "prospective_validation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(json.dumps(report, ensure_ascii=False, indent=2))
