# Ortak Analiz V4.5 - Data Quality Engine
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime.now(timezone.utc)
TODAY = NOW.astimezone(
    timezone(timedelta(hours=3))
).date()

errors = []
warnings = []

def load(name):
    try:
        data = json.loads(
            (ROOT / name).read_text(encoding="utf-8")
        )
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON structure")
        return data
    except Exception as exc:
        errors.append(f"{name}: {exc}")
        return {}

def timestamp(value):
    dt = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )
    if dt.tzinfo is None:
        raise ValueError("Missing timezone")
    return dt

def freshness(name, data, limit):
    try:
        age = (
            NOW - timestamp(data["updatedAt"])
        ).total_seconds() / 3600

        if age > limit or age < -0.1:
            errors.append(f"{name}: invalid data age")

        return round(age, 2)
    except Exception:
        errors.append(f"{name}: invalid timestamp")
        return None

def probability(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and 0 <= value <= 1
    )

daily = load("daily.json")
odds = load("odds.json")
archive = load("prospective_archive.json")
validation = load("prospective_validation.json")

ages = {
    "daily": freshness("daily", daily, 24),
    "odds": freshness("odds", odds, 18),
    "validation": freshness(
        "validation", validation, 24
    )
}

if daily.get("date") != TODAY.isoformat():
    errors.append("Daily report date mismatch")

if (
    not daily.get("leaguesChecked")
    or daily.get("leaguesLoaded")
    != daily.get("leaguesChecked")
):
    errors.append("Incomplete league coverage")

seen = set()
duplicates = 0
invalid = 0
overdue = 0
settled = 0

for key, record in archive.items():
    try:
        match_date = datetime.fromisoformat(
            record["date"]
        ).date()

        identity = (
            record["date"],
            record["league"],
            record["home"].strip().casefold(),
            record["away"].strip().casefold()
        )

        if identity in seen:
            duplicates += 1

        seen.add(identity)

        if (
            not identity[2]
            or not identity[3]
            or identity[2] == identity[3]
        ):
            raise ValueError("Invalid teams")

        recorded = timestamp(record["recordedAt"])

        if recorded > NOW:
            raise ValueError("Future timestamp")

        local_recorded = recorded.astimezone(
            timezone(timedelta(hours=3))
        )

        if local_recorded.date() >= match_date:
            raise ValueError("Late prediction")

        for field in ("old", "candidate", "baseline"):
            if not probability(record[field]):
                raise ValueError("Invalid probability")

        result = record["result"]

        if result is not None:
            if (
                not isinstance(result, list)
                or len(result) != 2
                or not all(
                    type(x) is int and x >= 0
                    for x in result
                )
                or match_date >= TODAY
            ):
                raise ValueError("Invalid result")

            settled += 1

        elif match_date < TODAY - timedelta(days=2):
            overdue += 1

    except Exception:
        invalid += 1

if duplicates:
    errors.append(f"Duplicate matches: {duplicates}")

if invalid:
    errors.append(f"Invalid archive records: {invalid}")

if overdue:
    warnings.append(f"Overdue results: {overdue}")

if not archive:
    errors.append("Empty prospective archive")

if validation.get("recorded") != len(archive):
    errors.append("Archive count mismatch")

if validation.get("tested") != settled:
    errors.append("Settled count mismatch")

if validation.get("pending") != len(archive) - settled:
    errors.append("Pending count mismatch")

if validation.get("errors"):
    errors.append("Model validation source errors")

event_ids = set()
valid_events = 0

events = odds.get("events", [])

if not isinstance(events, list):
    errors.append("Invalid odds events")
    events = []

for event in events:
    try:
        event_id = event["id"]

        if not event_id or event_id in event_ids:
            raise ValueError("Duplicate or missing event ID")

        event_ids.add(event_id)

        kickoff = timestamp(event["kickoff"])

        if kickoff <= NOW:
            continue

        valid_lines = 0

        for bookmaker in event.get("bookmakers", []):
            for line in bookmaker.get("lines", []):
                if line.get("point") != 2.5:
                    continue

                over = line["over"]
                under = line["under"]

                if not all(
                    type(x) in (int, float)
                    and math.isfinite(x)
                    and x > 1
                    for x in (over, under)
                ):
                    continue

                updated = timestamp(line["lastUpdate"])
                age = (NOW - updated).total_seconds()

                if 0 <= age <= 18 * 3600:
                    valid_lines += 1

        if valid_lines:
            valid_events += 1

    except Exception:
        errors.append("Invalid odds event")

if not valid_events:
    errors.append("No valid upcoming odds events")

report = {
    "version": "4.5",
    "updatedAt": NOW.isoformat(),
    "status": (
        "blocked" if errors
        else "warning" if warnings
        else "healthy"
    ),
    "qualityGate": "PAS" if errors or warnings else "PASS",
    "dataAgeHours": ages,
    "archiveRecords": len(archive),
    "settled": settled,
    "pending": len(archive) - settled,
    "duplicates": duplicates,
    "invalidRecords": invalid,
    "overdueResults": overdue,
    "validOddsEvents": valid_events,
    "minimumMatches": 500,
    "validationProgress": round(
        min(100, settled / 500 * 100), 2
    ),
    "liveEnabled": False,
    "errors": errors,
    "warnings": warnings
}

(ROOT / "data_quality.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(json.dumps(
    report, ensure_ascii=False, indent=2
))
