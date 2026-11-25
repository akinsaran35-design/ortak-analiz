import json
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent

MIN_PROB = 0.75
MIN_EV = 0.05
MIN_EDGE = 3.0
MIN_BOOKS = 3
MAX_AGE = 1800
MAX_SELECTIONS = 3
MIN_VALIDATED = 500

MARKETS = {"over15", "over25", "btts"}


def load(name):
    data = json.loads(
        (ROOT / name).read_text(encoding="utf-8")
    )
    if not isinstance(data, dict):
        raise ValueError("Invalid report")
    return data


def parse_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def fresh(value, now):
    try:
        age = (now - parse_time(value)).total_seconds()
        return 0 <= age <= MAX_AGE
    except (ValueError, TypeError, AttributeError):
        return False


def number(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
    )


def evaluate(row, now):
    try:
        if row["market"] not in MARKETS:
            return "unsupported_market"

        kickoff = parse_time(row["kickoff"])

        if kickoff <= now:
            return "already_started"

        if (
            kickoff + timedelta(hours=3)
        ).date() != (
            now + timedelta(hours=3)
        ).date():
            return "not_today"

        if not row.get("eventId"):
            return "missing_event"

        teams = row["match"].split(" – ")

        if len(teams) != 2 or not all(
            t.strip() for t in teams
        ):
            return "invalid_teams"

        books = row["bookCount"]

        if type(books) is not int or books < MIN_BOOKS:
            return "insufficient_bookmakers"

        p = row["modelProbabilityUncalibrated"]
        market = row["marketProbability"]
        odds = row["bestOdds"]

        if not all(number(x) for x in (p, market, odds)):
            return "invalid_numbers"

        if not 0 <= p <= 1 or not 0 < market < 1:
            return "invalid_probability"

        if odds <= 1:
            return "invalid_odds"

        if p < MIN_PROB:
            return "low_probability"

        if p * odds - 1 < MIN_EV:
            return "low_ev"

        if (p - market) * 100 < MIN_EDGE:
            return "low_model_edge"

        movement = row.get("movementPP")

        if (
            number(movement)
            and row.get("movementBookmakers", 0) >= MIN_BOOKS
            and movement <= -3.0
        ):
            return "negative_market_movement"

        return None

    except (KeyError, ValueError, TypeError, AttributeError):
        return "invalid_row"


def build_report(model, quality, validation, now):
    report = {
        "version": "4.13",
        "updatedAt": now.isoformat(),
        "mode": "research_only",
        "decision": "PAS",
        "realBettingEnabled": False,
        "maximumSelections": MAX_SELECTIONS,
        "minimumValidatedMatches": MIN_VALIDATED,
        "testedMatches": 0,
        "modelCalibrated": False,
        "researchCandidates": [],
        "selections": [],
        "rejected": {},
        "reasons": [],
        "errors": []
    }

    reasons = report["reasons"]

    tested = validation.get("tested", 0)

    if type(tested) is not int or tested < 0:
        tested = 0
        reasons.append("invalid_validation_count")

    report["testedMatches"] = tested

    if tested < MIN_VALIDATED:
        reasons.append("insufficient_validated_matches")

    if validation.get("liveEnabled") is not True:
        reasons.append("validation_not_approved")

    if validation.get("errors"):
        reasons.append("validation_errors")

    if model.get("modelCalibrated") is not True:
        reasons.append("model_not_calibrated")

    reasons.append("real_betting_locked")

    if (
        quality.get("qualityGate") != "PASS"
        or quality.get("status") != "healthy"
        or quality.get("errors") != []
        or quality.get("warnings") != []
        or not fresh(quality.get("updatedAt"), now)
    ):
        reasons.append("data_quality_failed")
        return report

    if (
        model.get("version") != "4.12"
        or model.get("errors") != []
        or not fresh(model.get("updatedAt"), now)
    ):
        reasons.append("model_report_invalid_or_stale")
        return report

    rows = model.get("rows")

    if not isinstance(rows, list):
        reasons.append("invalid_model_rows")
        return report

    eligible = []

    for row in rows:
        reason = evaluate(row, now)

        if reason:
            rejected = report["rejected"]
            rejected[reason] = rejected.get(reason, 0) + 1
            continue

        eligible.append(row)

    eligible.sort(
        key=lambda r: (
            r["modelProbabilityUncalibrated"],
            r["modelProbabilityUncalibrated"]
            * r["bestOdds"] - 1
        ),
        reverse=True
    )

    used_events = set()
    used_teams = set()

    for row in eligible:
        event = row["eventId"]

        teams = {
            t.strip().casefold()
            for t in row["match"].split(" – ")
        }

        if event in used_events or teams & used_teams:
            continue

        candidate = dict(row)

        candidate["decision"] = "RESEARCH_ONLY"

        candidate["estimatedEV"] = round(
            row["modelProbabilityUncalibrated"]
            * row["bestOdds"] - 1,
            6
        )

        report["researchCandidates"].append(candidate)

        used_events.add(event)
        used_teams.update(teams)

        if len(report["researchCandidates"]) >= MAX_SELECTIONS:
            break

    if not report["researchCandidates"]:
        reasons.append("no_eligible_candidates")

    return report


def main():
    now = datetime.now(timezone.utc)

    try:
        report = build_report(
            load("model_market.json"),
            load("data_quality.json"),
            load("prospective_validation.json"),
            now
        )

    except Exception as exc:
        report = {
            "version": "4.13",
            "updatedAt": now.isoformat(),
            "mode": "research_only",
            "decision": "PAS",
            "realBettingEnabled": False,
            "researchCandidates": [],
            "selections": [],
            "errors": [type(exc).__name__]
        }

    report["candidateCount"] = len(
        report["researchCandidates"]
    )

    (ROOT / "unified_decision.json").write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(json.dumps(
        report,
        ensure_ascii=False,
        indent=2
    ))


if __name__ == "__main__":
    main()
