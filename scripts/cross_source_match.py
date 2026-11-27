"""Conservative cross-provider fixture matching; no automatic settlement."""
from datetime import datetime
import unicodedata
def norm(s):
    return " ".join(unicodedata.normalize("NFKC",s).casefold().split())
def match(primary,secondary,competition_map):
    pairs=[]; unmatched=[]; used=set()
    for p in primary:
        candidates=[]
        for s in secondary:
            if competition_map.get(p["league"])!=s["competitionId"]:continue
            if norm(p["home"])!=norm(s["home"]) or norm(p["away"])!=norm(s["away"]):continue
            if datetime.fromisoformat(p["kickoff"].replace("Z","+00:00"))!=datetime.fromisoformat(s["kickoff"].replace("Z","+00:00")):continue
            candidates.append(s)
        if len(candidates)!=1 or candidates[0]["eventId"] in used:
            unmatched.append(p["eventId"]);continue
        s=candidates[0];used.add(s["eventId"])
        a=p.get("score");b=s.get("score")
        pairs.append(dict(primaryId=p["eventId"],secondaryId=s["eventId"],scoreAgreement=(a==b if a is not None and b is not None else None)))
    return dict(pairs=pairs,unmatched=unmatched,settlementEnabled=False)
