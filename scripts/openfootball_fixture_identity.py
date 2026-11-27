"""Verify alternative fixture identity against season-wide unique pairs and source event IDs.
Research evidence only; never change the original archive or publish model inputs.
"""
import json, sys, hashlib
from collections import Counter
from datetime import date
from pathlib import Path
from openfootball_score_audit import ROOT, CODES, key, csv_index, full_time
from openfootball_third_source_audit import LEAGUES, read, espn_index

def season_pair(k):
    return k[1:]

def assess(row, archive, csv, events, code):
    original=key(row["originalDate"],row["home"],row["away"],code)
    alternative=key(row["alternativeDate"],row["home"],row["away"],code)
    pair=season_pair(original)
    source=[m for m in archive if season_pair(key(m["date"],m["team1"],m["team2"],code))==pair]
    independent=[(k,s) for k,s in csv.items() if season_pair(k)==pair]
    candidates=events.get(alternative,[])
    checks=dict(
        sourcePairUnique=len(source)==1,
        sourceOriginalMatches=len(source)==1 and source[0]["date"]==row["originalDate"] and full_time(source[0])==row["originalScore"],
        sourceRoundPresent=len(source)==1 and isinstance(source[0].get("round"),str) and bool(source[0]["round"]),
        independentPairUnique=len(independent)==1,
        independentDateScoreMatches=len(independent)==1 and independent[0]==(alternative,[row["alternativeScore"]]),
        espnEventUnique=len(candidates)==1,
        espnIdAndScoreMatch=len(candidates)==1 and candidates[0]["eventId"]==row["espnEventId"] and candidates[0]["score"]==row["alternativeScore"],
        dateInSeason=date(2025,7,1)<=date.fromisoformat(row["alternativeDate"])<=date(2026,6,30),
        deltaMatches=(date.fromisoformat(row["alternativeDate"])-date.fromisoformat(row["originalDate"])).days==row["deltaDays"])
    return dict(row,round=source[0].get("round") if len(source)==1 else None,checks=checks,
        status="unique_season_pair_corroborated" if all(checks.values()) else "identity_unresolved",
        espnEvidence=candidates)

def main():
    doc=json.loads((ROOT/"research/openfootball/reconciled-score-evidence-2026-11-27.json").read_text())
    rows=doc["alternativeDateReview"]
    assert len(rows)==51
    assert len({r["espnEventId"] for r in rows})==51
    assert not ({r["espnEventId"] for r in rows}&{r["espnEventId"] for r in doc["confirmedSameDateCorrections"]})
    reports=[];sources=[];errors=[]
    for code in sorted({r["league"] for r in rows}):
        archive=json.loads((ROOT/"research/openfootball/2025-26"/(code+".json")).read_text())
        csv_url="https://football-data.co.uk/mmz4281/2526/"+CODES[code]+".csv"
        raw=read(csv_url);csv=csv_index(raw)
        sources.append(dict(league=code,url=csv_url,sha256=hashlib.sha256(raw).hexdigest(),sourceBlobSha=archive["sourceBlobSha"]))
        espn,tz=LEAGUES[code]
        subset=[r for r in rows if r["league"]==code]
        events={}
        for day in sorted({r["alternativeDate"] for r in subset}):
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{espn}/scoreboard?dates="+day.replace("-","")
            try:
                raw=read(url);part=espn_index(json.loads(raw),code,tz)
                events.update({k:v for k,v in part.items() if k[0]==day})
                sources.append(dict(league=code,date=day,url=url,sha256=hashlib.sha256(raw).hexdigest()))
            except (OSError,ValueError,KeyError,TypeError) as exc:
                errors.append(dict(league=code,date=day,error=str(exc)))
        for row in subset:
            result=assess(row,archive["matches"],csv,events,code)
            reports.append(result)
            print("IDENTITY_REVIEW",json.dumps(result,ensure_ascii=False))
    counts=dict(Counter(r["status"] for r in reports))
    report=dict(mode="historical_fixture_identity_evidence",archiveModified=False,roundSource="OpenFootball only; not independently verified",identityRule="unique oriented team pair in league season in both archives; exact alternative date and ESPN event identity and matching independent final scores",counts=counts,rows=reports,sources=sources,errors=errors)
    Path("openfootball_fixture_identity.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("IDENTITY_TOTAL",json.dumps(dict(counts=counts,errors=errors)))
    if len(reports)!=51 or errors:raise SystemExit("audit incomplete")

def self_test():
    r=dict(originalDate="2025-11-15",alternativeDate="2025-11-16",home="Luton Town",away="AFC Wimbledon",originalScore=[2,0],alternativeScore=[1,0],deltaDays=1,espnEventId="123")
    m=dict(date=r["originalDate"],team1=r["home"],team2=r["away"],round="16. Round",score={"ft":[2,0]})
    k=("2025-11-16","luton","afc wimbledon")
    csv={k:[[1,0]]};events={k:[dict(eventId="123",score=[1,0])]}
    assert assess(r,[m],csv,events,"en.3")["status"]=="unique_season_pair_corroborated"
    assert assess(r,[m,m],csv,events,"en.3")["status"]=="identity_unresolved"
    assert assess(r,[m],csv,{k:[dict(eventId="999",score=[1,0])]},"en.3")["status"]=="identity_unresolved"
    assert assess(r,[m],{**csv,("2025-11-17",*k[1:]):[[1,0]]},events,"en.3")["status"]=="identity_unresolved"
    print("Fixture identity self-tests passed")

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    else:main()
