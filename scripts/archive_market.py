import json
from pathlib import Path
from datetime import datetime
from statistics import median

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
        record["observations"].append({"observedAt":observed,"marketProbability":row["marketProbability"],"modelProbabilityUncalibrated":row["modelProbabilityUncalibrated"],"bookCount":row["bookCount"],"bookProbabilities":row.get("bookProbabilities",{})})
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
        record["observationCount"] = len(obs)
        record["distinctProbabilityCount"] = len({x["marketProbability"] for x in obs})
        record["movementStatus"] = ("insufficient_observations" if len(obs)<2 else
                                    "unchanged" if record["distinctProbabilityCount"] == 1 else
                                    "observed_change")
        record["observationSpanMinutes"] = round((datetime.fromisoformat(obs[-1]["observedAt"].replace("Z","+00:00")) - datetime.fromisoformat(obs[0]["observedAt"].replace("Z","+00:00"))).total_seconds()/60,2) if obs else 0
        comparable = [x for x in obs if x.get("bookProbabilities")]
        first = comparable[0]["bookProbabilities"] if len(comparable)>=2 else {}
        last = comparable[-1]["bookProbabilities"] if len(comparable)>=2 else {}
        common = sorted(first.keys() & last.keys())
        record["commonBookCount"] = len(common)
        record["sameBookProbabilityChange"] = round(median(last[k]-first[k] for k in common),6) if len(common)>=3 else None
        record["sameBookStatus"] = "comparable" if len(common)>=3 else "insufficient_data"
    path.write_text(json.dumps({"version":"3.4","decision":"PAS","events":events},ensure_ascii=False,indent=2),encoding="utf-8")
    print("Archived events:",len(events))

if __name__ == "__main__":
    main()
