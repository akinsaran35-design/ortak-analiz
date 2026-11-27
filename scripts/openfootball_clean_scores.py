"""Build a separate research-only archive of corroborated historical final scores."""
import json, hashlib, sys
from collections import Counter
from pathlib import Path
from openfootball_score_audit import ROOT, CODES, compare, csv_index, key
from openfootball_third_source_audit import read

def main():
    base=ROOT/"research/openfootball"
    corrections=json.loads((base/"reconciled-score-evidence-2026-11-27.json").read_text())
    identity=json.loads((base/"fixture-identity-evidence-2026-11-27.json").read_text())
    def original_key(x,day):return (x["league"],x[day],x["home"],x["away"])
    same={original_key(x,"date"):x for x in corrections["confirmedSameDateCorrections"]}
    shifted={original_key(x,"originalDate"):x for x in identity["rows"]}
    assert len(same)==85 and len(shifted)==51 and not set(same)&set(shifted)
    assert all(x["status"]=="unique_season_pair_corroborated" and x["checks"] and all(x["checks"].values()) for x in shifted.values())
    rows=[];sources=[];used=set();identities=set();event_ids=set()
    for code,division in CODES.items():
        archive=json.loads((base/"2025-26"/(code+".json")).read_text())
        url="https://football-data.co.uk/mmz4281/2526/"+division+".csv"
        raw=read(url);index=csv_index(raw)
        sources.append(dict(league=code,openfootballBlobSha=archive["sourceBlobSha"],csvUrl=url,csvSha256=hashlib.sha256(raw).hexdigest()))
        for m in compare(archive["matches"],index,code):
            k=original_key(dict(league=code,**m),"date")
            event=None
            if k in same:
                e=same[k]
                assert m["status"]=="score_conflict" and m["openfootball"]==e["originalScore"] and m["independent"]==e["corroboratedScore"]
                day=m["date"];score=e["corroboratedScore"];event=e["espnEventId"];status="corrected_score";used.add(k)
            elif k in shifted:
                e=shifted[k];day=e["alternativeDate"];score=e["alternativeScore"];event=e["espnEventId"];status="corrected_date";used.add(k)
                assert m["status"]=="unmatched" and m["openfootball"]==e["originalScore"]
                assert index.get(key(day,m["home"],m["away"],code))==[score]
            else:
                assert m["status"]=="matched"
                day=m["date"];score=m["openfootball"];status="original_match"
            unique=(code,*key(day,m["home"],m["away"],code))
            assert unique not in identities
            identities.add(unique)
            if event:
                assert event not in event_ids
                event_ids.add(event)
            rows.append(dict(league=code,season="2025-26",date=day,home=m["home"],away=m["away"],ft=score,originalDate=m["date"],originalFT=m["openfootball"],status=status,espnEventId=event,sourcePair=["Football-Data","OpenFootball" if status=="original_match" else "ESPN"]))
    counts=dict(Counter(x["status"] for x in rows))
    assert used==set(same)|set(shifted)
    assert counts=={"original_match":724,"corrected_score":85,"corrected_date":51}
    assert len(rows)==len(identities)==860 and len(event_ids)==136
    report=dict(mode="historical_research_only",version="6.18",modelApproved=False,originalArchiveModified=False,scope="Final scores and fixture dates only; no halftime, kickoff or round verification; not prospective validation",counts=counts,sources=sources,evidenceRuns=[46050715333,46051728902,46052684952,46054026516],rows=sorted(rows,key=lambda x:(x["league"],x["date"],x["home"],x["away"])))
    Path("openfootball_clean_scores.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("CLEAN_TOTAL",json.dumps(dict(counts=counts,uniqueFixtures=len(identities),uniqueEspnIds=len(event_ids),modelApproved=False)))

if __name__=="__main__":main()
