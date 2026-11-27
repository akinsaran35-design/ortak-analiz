"""Historical source labels only; no identity or assignment inference."""
from datetime import datetime
from collections import defaultdict
import json
from historical_referee_coverage import build as historical
from results_source_pilot import TR

def audit(report):
    groups=[]
    for g in report["groups"]:
        labels=defaultdict(list)
        for s in g["seasons"]:
            for r in s["labels"]:
                labels[r["label"]].append(dict(season=s["season"],matches=r["matches"],yellowCards=r["yellowCards"],redCards=r["redCards"]))
        profiles=[]
        for label, seasons in sorted(labels.items()):
            metrics={}
            for metric in ("yellowCards","redCards"):
                n=sum(s[metric]["sample"] for s in seasons)
                total=sum(s[metric]["sample"]*s[metric]["totalAverage"] for s in seasons if s[metric]["sample"] and s[metric]["totalAverage"] is not None)
                metrics[metric]=dict(sample=n,mean=total/n if n else None,minimumSampleMet=n>=30)
            profiles.append(dict(label=label,seasons=seasons,metrics=metrics,identityVerified=False))
        groups.append(dict(league=g["league"],completedMatches=g["completedMatches"],assignedFixtures=g["assignedFixtures"],coverage=g["coverage"],errors=g["errors"],profiles=profiles))
    return dict(version="5.54",cutoffExclusive=report["cutoffExclusive"],identityVerified=False,upcomingAssignmentsVerified=False,predictionsEnabled=False,decision="PAS",groups=groups)

if __name__=="__main__":
    print(json.dumps(audit(historical(datetime.now(TR))),ensure_ascii=False))
