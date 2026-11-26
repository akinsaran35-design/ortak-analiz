import unittest
from datetime import datetime,timedelta
from live_frozen_evidence import freeze,build
from live_result_evidence import update
from live_performance_research import archive,evaluate
from results_source_pilot import TR
from live_statistics_pilot import BASE,SOURCES
from multi_league_results import source_urls
PRE=datetime(2026,11,26,16,0,tzinfo=TR)
KICK=PRE+timedelta(hours=1)
NOW=KICK+timedelta(minutes=55)
def inputs():
    d=dict(updatedAt=(PRE-timedelta(minutes=10)).isoformat(),candidates=[dict(date=PRE.date().isoformat(),league="İngiltere Premier Lig",match="A – B",expectedGoals=dict(home=1.5,away=1.2))])
    c=dict(version="4.92",source="ESPN",mode="research_only",dailyUpdatedAt=d["updatedAt"],updatedAt=(PRE-timedelta(minutes=5)).isoformat(),dates=[PRE.date().isoformat()],rows=[dict(league="en.1",status="same_date",published=[dict(date=PRE.date().isoformat(),league="İngiltere Premier Lig",match="A – B")],espn=[dict(date=PRE.date().isoformat(),eventId="123",kickoff=KICK.isoformat(),match="A FC – B")])])
    return d,c
def snap():
    row=dict(league="en.1",eventId="123",home="A FC",away="B",kickoff=KICK.isoformat(),source=BASE+SOURCES["en.1"][1]+"/summary?event=123",receivedAt=NOW.isoformat(),error=None,observation=dict(state="in",score=[1,0],clock="54'",metrics=dict(corners=[4,1],shots=[8,3],shotsOnTarget=[3,1],yellowCards=[1,0],redCards=[0,0],possession=[60,40])))
    return dict(mode="live_snapshot_only",source="ESPN",updatedAt=NOW.isoformat(),rows=[row])
class Tests(unittest.TestCase):
    def test_freeze_and_replay(self):
        d,c=inputs()
        f=freeze(d,c,{},PRE)
        self.assertEqual(len(f),1)
        self.assertEqual(freeze(d,c,{},NOW),{})
        d["updatedAt"]=NOW.isoformat()
        self.assertEqual(freeze(d,c,f,NOW),f)
        r=build(snap(),f,NOW)
        self.assertEqual(r["counts"],{"conditional_scenario":1})
        a=archive(r,{},NOW)
        self.assertEqual(len(a),1)
        self.assertEqual(build(snap(),{},NOW)["counts"],{"no_frozen_prematch_evidence":1})
    def test_corroboration(self):
        d,c=inputs();a=archive(build(snap(),freeze(d,c,{},PRE),NOW),{},NOW)
        later=NOW+timedelta(days=1)
        def probe(records,now):
            self.assertEqual(len(records),1)
            return dict(version="4.69",updatedAt=now.isoformat(),groups=[dict(league="en.1",date=PRE.date().isoformat(),sources=list(source_urls("en.1",PRE.date().isoformat())),errors=[],rows=[dict(date=PRE.date().isoformat(),home="A FC",away="B",csv=[2,0],espn=[2,0],status="corroborated")])])
        result=update(a,{},later,probe)
        self.assertEqual(len(result["verified"]),1)
        self.assertEqual(evaluate(a,result["verified"],later)["counts"],{"evaluated":1})
        self.assertEqual(update(a,result,later,lambda *x:self.fail("unnecessary fetch"))["groupsQueried"],0)
    def test_missing_and_conflicting(self):
        d,c=inputs();a=archive(build(snap(),freeze(d,c,{},PRE),NOW),{},NOW)
        later=NOW+timedelta(days=1)
        def probe(records,now):
            return dict(version="4.69",updatedAt=now.isoformat(),groups=[dict(league="en.1",date=PRE.date().isoformat(),sources=list(source_urls("en.1",PRE.date().isoformat())),errors=[],rows=[dict(date=PRE.date().isoformat(),home="A FC",away="B",csv=[2,0],espn=[1,0],status="conflict")])])
        r=update(a,{},later,probe)
        self.assertEqual(len(r["blocked"]),1)
        self.assertEqual(r["verified"],[])
        self.assertEqual(update(a,r,later,lambda *x:self.fail("too soon"))["groupsQueried"],0)
if __name__=="__main__":unittest.main()
