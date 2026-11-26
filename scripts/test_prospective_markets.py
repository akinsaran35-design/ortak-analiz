import unittest,copy
from datetime import datetime,timezone,timedelta,date
from prospective_markets import capture,summarize,MARKETS

class MarketTests(unittest.TestCase):
    def test_capture_and_no_backfill(self):
        now=datetime(2026,11,30,18,tzinfo=timezone(timedelta(hours=3)))
        history=[(date(2026,11,20),"A","B",2,1),(date(2026,11,21),"C","D",1,0)]
        p=capture(history,[.8,.6,.5],[.7,.55,.4])
        self.assertEqual([p[m]["baseline"] for m in MARKETS],[.5,.5,.5])
        r=dict(date="2026-11-28",recordedAt="2026-11-26T12:00:00+03:00",result=[2,1],old=.6,candidate=.55,baseline=.5)
        records={"legacy":dict(r),"new":dict(r,prospectiveMarkets=p),"pending":dict(r,prospectiveMarkets=p,date="2026-12-01",result=None),"late":dict(r,recordedAt="2026-11-28T12:00:00+03:00",prospectiveMarkets=p)}
        original=copy.deepcopy(records)
        out=summarize(records,now)
        self.assertEqual(records,original)
        self.assertEqual(out["1.5 Üst"]["tested"],1)
        self.assertEqual(out["1.5 Üst"]["legacyWithoutForecast"],1)
        self.assertEqual(out["2.5 Üst"]["tested"],2)
        self.assertEqual(out["KG Var"]["pending"],1)
        self.assertEqual(out["KG Var"]["invalid"],1)
        self.assertAlmostEqual(out["1.5 Üst"]["scores"]["candidate"],.09)
        self.assertAlmostEqual(out["KG Var"]["scores"]["candidate"],.36)
        self.assertTrue(all(not x["liveEnabled"] for x in out.values()))
        with self.assertRaises(ValueError): capture(history,[.8,.6,.5],[.7,float("nan"),.4])
    def test_incoherent_capture_and_archived_forecast(self):
        now=datetime(2026,11,30,18,tzinfo=timezone(timedelta(hours=3)))
        history=[(date(2026,11,20),"A","B",2,1)]
        with self.assertRaises(ValueError):capture(history,[.4,.6,.2],[.7,.55,.4])
        with self.assertRaises(ValueError):capture(history,[.6,.5,.7],[.7,.55,.4])
        p=capture(history,[.8,.6,.5],[.7,.55,.4])
        row=dict(date="2026-11-28",recordedAt="2026-11-26T12:00:00+03:00",result=[2,1],old=.6,candidate=.55,baseline=1,prospectiveMarkets=p)
        bad=copy.deepcopy(row);bad["prospectiveMarkets"]["2.5 Üst"]["old"]=.61
        impossible=copy.deepcopy(row);impossible["prospectiveMarkets"]["KG Var"]["candidate"]=.9
        out=summarize({"good":row,"divergence":bad,"impossible":impossible},now)
        for m in MARKETS:
            self.assertEqual(out[m]["tested"],1)
            self.assertEqual(out[m]["invalid"],2)
    def test_calibration_diagnostics(self):
        now=datetime(2026,11,30,18,tzinfo=timezone(timedelta(hours=3)))
        r=dict(date="2026-11-28",recordedAt="2026-11-26T12:00:00+03:00",result=[2,1],old=.6,candidate=.8,baseline=.5)
        records={"a":r,"b":dict(r,result=[0,0],candidate=.4),"pending":dict(r,result=None)}
        normal=summarize(records,now)
        enriched=summarize(records,now,include_calibration=True)
        x=enriched["2.5 Üst"]["calibration"]
        self.assertEqual(x["sample"],2)
        self.assertEqual(x["observedRate"],.5)
        self.assertAlmostEqual(x["meanPrediction"]["candidate"],.6)
        self.assertAlmostEqual(x["gapPP"]["candidate"],10)
        self.assertFalse(x["sampleAdequate"])
        self.assertTrue(x["descriptiveOnly"])
        self.assertIsNone(enriched["KG Var"]["calibration"]["observedRate"])
        self.assertEqual(enriched["KG Var"]["calibration"]["meanPrediction"],{})
        for m in MARKETS:
            self.assertEqual({k:v for k,v in enriched[m].items() if k!="calibration"},normal[m])
if __name__=="__main__": unittest.main()
