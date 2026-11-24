import json
from pathlib import Path
from datetime import datetime

def archive(previous, report, odds):
    events = {e["id"]: e for e in odds["events"]}
    observed = odds["updatedAt"]
    for row in report["rows"]:
        event = events.get(row["eventId"])
        if not event or datetime.fromisoformat(observed.replace("Z","+00:00")) >= datetime.fromisoformat(event["kickoff"].replace("Z","+00:00")):
            continue
        record = previous.setdefault(row["eventId"], {"match":row["match"],"kickoff":event["kickoff"],"observations":[]})
        if any(x["observedAt"] == observed for x in record["observations"]):
            continue
        record["observations"].append({"observedAt":observed,"marketProbability":row["marketProbability"],"modelProbabilityUncalibrated":row["modelProbabilityUncalibrated"],"bookCount":row["bookCount"]})
        record["observations"].sort(key=lambda x:x["observedAt"])
    return previous

def main():
    path = Path("market_archive.json")
    previous = json.loads(path.read_text(encoding="utf-8"))["events"] if path.exists() else {}
    report = json.loads(Path("market_analysis.json").read_text(encoding="utf-8"))
    odds = json.loads(Path("odds.json").read_text(encoding="utf-8"))
    events = archive(previous,report,odds)
    for record in events.values():
        obs = record["observations"]
        record["probabilityChange"] = round(obs[-1]["marketProbability"]-obs[0]["marketProbability"],4) if len(obs)>1 else None
    path.write_text(json.dumps({"version":"3.0","decision":"PAS","events":events},ensure_ascii=False,indent=2),encoding="utf-8")
    print("Archived events:",len(events))

if __name__ == "__main__":
    main()
