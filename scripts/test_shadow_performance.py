import unittest
from datetime import datetime, timezone, timedelta
from shadow_performance import archive_coupon, settle, metrics
from shadow_results import resolve
from shadow_coupon import select

class ShadowTests(unittest.TestCase):
    def test_coupon(self):
        now = datetime(2026,11,25,12,tzinfo=timezone.utc)
        kickoff = now + timedelta(hours=2)
        picks = [{"eventId":str(i),"kickoff":kickoff.isoformat(),"market":"2.5 Over","odds":1.5} for i in range(3)]
        records = {}
        coupon = {"mode":"shadow","liveEnabled":False,"selections":picks}
        archive_coupon(records,coupon,now)
        archive_coupon(records,coupon,now)
        self.assertEqual(len(records),1)
        later = now + timedelta(days=1)
        results = {str(i):{"status":"final","score":[2,1]} for i in range(3)}
        settle(records,{},later)
        self.assertEqual(metrics(list(records.values()))["pending"],1)
        settle(records,results,later)
        self.assertEqual(metrics(list(records.values()))["profit"],237.5)
        self.assertEqual(metrics(list(records.values()))["roi"],2.375)
        records = {}
        archive_coupon(records,coupon,now)
        results["0"]["score"] = [0,0]
        settle(records,results,later)
        self.assertEqual(metrics(list(records.values()))["profit"],-100)
    def test_shadow_window(self):
        # Artificial test fixtures only; never publish these as actual predictions.
        now=datetime(2026,11,27,20,30,tzinfo=timezone.utc)
        def event(eid,hours):
            return {"id":eid,"league":"test","home":eid+"H","away":eid+"A","kickoff":(now+timedelta(hours=hours)).isoformat(),"bookmakers":[{"key":str(i),"name":"fixture","lines":[{"point":2.5,"over":1.6,"lastUpdate":now.isoformat()}]} for i in range(3)]}
        events=[event("next",18),event("far",25),event("past",-1),event("low",2)]
        analysis={"market":"2.5","snapshotFresh":True,"updatedAt":now.isoformat(),"rows":[{"eventId":e["id"],"match":e["id"],"modelProbabilityUncalibrated":.8 if e["id"]!="low" else .7} for e in events]}
        odds={"updatedAt":now.isoformat(),"errors":[],"events":events}
        result=select(analysis,odds,now)
        self.assertEqual([x["eventId"] for x in result["selections"]],["next"])
        self.assertEqual(result["decision"],"SHADOW_ONLY")
        self.assertFalse(result["liveEnabled"])
        self.assertEqual(result["diagnostics"]["rejected"],{"outside_research_window":1,"started":1,"probability_below_threshold_or_invalid":1})
        self.assertEqual(select(analysis,odds,now+timedelta(minutes=31))["selections"],[])
    def test_score_matching(self):
        now = datetime(2026,11,26,12,tzinfo=timezone.utc)
        p = {"eventId":"a","kickoff":"2026-11-25T18:00:00+00:00","league":"soccer_epl","match":"Home FC – Away FC"}
        records = {"x":{"status":"pending","selections":[p]}}
        results = {}
        fixture = {"date":"2026-11-25","team1":"Home FC","team2":"Away FC","score":{"ft":[2,1]}}
        resolve(records,results,now,lambda *args:[fixture,fixture])
        self.assertEqual(results,{})
        resolve(records,results,now,lambda *args:[fixture])
        self.assertEqual(results["a"]["score"],[2,1])
        results.clear()
        fixture["team1"] = {"name":"Home FC"}
        fixture["team2"] = {"name":"Away FC"}
        self.assertEqual(resolve(records,results,now,lambda *args:[fixture]),[])
        self.assertEqual(results["a"]["score"],[2,1])
        results.clear()
        self.assertEqual(resolve(records,results,now,lambda *args:[fixture,fixture])[0]["error"],"ambiguous_fixture")
        self.assertEqual(results,{})
        fixture["score"] = {}
        self.assertEqual(resolve(records,results,now,lambda *args:[fixture])[0]["error"],"final_score_unavailable")
        self.assertEqual(results,{})

if __name__ == "__main__":
    unittest.main()
