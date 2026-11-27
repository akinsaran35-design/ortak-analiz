# Ortak Analiz V4.4 - Prospective validation
import json
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

from backtest import LEAGUES, fetch, team, predict, weighted_predict
from prospective_markets import capture, summarize
from prospective_capture_window import HORIZON_DAYS, identity, existing_identities, capture_status
from collections import Counter
from prospective_history import canonical_history, team_counts

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
existing = existing_identities(records)
capture_counts = Counter()
missing_history = []
history_audit = {}
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

    normalized, history_audit[league] = canonical_history(league,history,TODAY)

    for (d, h, a), ft in sorted(fixtures.items()):
        key = json.dumps(
            [d.isoformat(), league, h, a],
            ensure_ascii=False
        )

        try:
            status = capture_status(league,d,h,a,ft,TODAY,existing,blocked)
        except (KeyError,ValueError,TypeError):
            capture_counts["invalid_identity"] += 1
            continue
        if status != "eligible":
            if status == "calendar_blocked": calendar_duplicate_prevented += 1
            if status != "outside_future_window": capture_counts[status] += 1
            continue

        training = history
        normalization = "source_names"
        old = predict(training, h, a)
        new = weighted_predict(training, h, a)

        if old is None or new is None or not training:
            _,_,hk,ak = identity(league,d.isoformat(),h,a)
            training = normalized
            old = predict(training,hk,ak)
            new = weighted_predict(training,hk,ak)
            normalization = "canonical_exact"
            if old is None or new is None or not training:
                capture_counts["insufficient_history"] += 1
                missing_history.append(dict(league=league,date=d.isoformat(),home=h,away=a,sourceSamples=team_counts(history,h,a),canonicalSamples=team_counts(normalized,hk,ak)))
                continue

        baseline = sum(
            int(x[3] + x[4] >= 3)
            for x in training
        ) / len(training)

        try:
            markets = capture(training,old,new)
        except ValueError:
            errors.append(f"{league}/{d}/{h}/{a}: inconsistent model probabilities")
            continue

        records[key] = {
            "date": d.isoformat(),
            "league": league,
            "home": h,
            "away": a,
            "recordedAt": NOW.isoformat(),
            "modelVersion": "4.4",
            "historyNormalization": normalization,
            "old": old[1],
            "candidate": new[1],
            "baseline": baseline,
            "prospectiveMarkets": markets,
            "result": None
        }
        existing.add(identity(league,d.isoformat(),h,a))
        capture_counts["new"] += 1
        if normalization == "canonical_exact":capture_counts["recovered_identity"] += 1

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
# Date-based research status, not a claim about individual kickoff or completion.
pending_dates = Counter()
for record in records.values():
    if record["result"] is not None:
        continue
    try:
        fixture_date = date.fromisoformat(record["date"])
    except (KeyError, TypeError, ValueError):
        pending_dates["invalidDate"] += 1
        continue
    pending_dates["future" if fixture_date > TODAY else "today" if fixture_date == TODAY else "past"] += 1
pending_date_status = {k: pending_dates[k] for k in ("future", "today", "past", "invalidDate")}
assert sum(pending_date_status.values()) == len(records) - n

report = {
    "version": "4.4",
    "market": "2.5 Ust",
    "candidate": "weightedBrier",
    "updatedAt": NOW.isoformat(),
    "recorded": len(records),
    "verifiedFallbackSettled": verified_count,
    "calendarDuplicatePrevented": calendar_duplicate_prevented,
    "captureWindowDays": HORIZON_DAYS,
    "captureCounts": dict(capture_counts),
    "missingHistory": missing_history,
    "historyIdentityAudit": history_audit,
    "tested": n,
    "pending": len(records) - n,
    "pendingDateStatus": pending_date_status,
    "pendingDateStatusAsOf": TODAY.isoformat(),
    "minimumMatches": 500,
    "liveEnabled": False,
    "status": "collecting_data",
    "errors": errors,
    "marketResearchVersion": "4.85",
    "classificationVersion": "6.19",
    "marketResearch": summarize(records,NOW)
}

if report["marketResearch"]["2.5 Üst"]["tested"]:
    scores = report["marketResearch"]["2.5 Üst"]["scores"]

    report["scores"] = scores
    report["improvement"] = (
        scores["baseline"] - scores["candidate"]
    )

    if report["marketResearch"]["2.5 Üst"]["tested"] >= 500 and not errors and all(x["invalid"]==0 for x in report["marketResearch"].values()):
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
