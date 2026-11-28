import unittest,json,copy
from datetime import datetime
from extra_ml_prospective import capture,empty_ledger
from extra_ml_settlement import settle,summarize
from test_extra_ml_preflight import PreflightTests
from results_source_pilot import TR

class SettlementTests(unittest.TestCase):
    def setUp(self):
        f=PreflightTests()
        f.setUp()
        self.meta=dict(modelSha256="test-hash",frozenAt="2026-11-28T09:00:00+03:00",featureKeys=sorted(f.keys))
        class Stub:
            def predict_proba(self,x):
                return [[.2,.2,.2,.2,.2] for _ in x]
        self.ledger=empty_ledger(self.meta)
        capture(self.ledger,f.rows,[f.fixture],Stub(),self.meta,f.now)
        self.now=datetime(2026,12,1,12,tzinfo=TR)
        self.csv=b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n29/11/2026,Hearts,Celtic,2,1\n"
        self.payload=dict(events=[dict(id="123",date="2026-11-29T12:00:00Z",competitions=[
            dict(date="2026-11-29T12:00:00Z",status=dict(type=dict(completed=True,name="STATUS_FULL_TIME")),
            competitors=[dict(homeAway="home",team=dict(displayName="Heart of Midlothian"),score="2"),
            dict(homeAway="away",team=dict(displayName="Celtic"),score="1")])])])
    def reader(self,url):
        return self.csv if "football-data" in url else json.dumps(self.payload).encode()
    def test_verified_and_immutable_forecast(self):
        original=copy.deepcopy(self.ledger["forecasts"])
        self.assertEqual(settle(self.ledger,self.meta,self.now,self.reader)[0],1)
        self.assertEqual(settle(self.ledger,self.meta,self.now,self.reader)[0],0)
        self.assertEqual(original,self.ledger["forecasts"])
        self.assertEqual(summarize(self.ledger)["validSettled"],1)
        self.assertFalse(summarize(self.ledger)["sampleTargetReached"])
    def test_pending_and_conflict(self):
        self.payload["events"][0]["competitions"][0]["status"]["type"]["completed"]=False
        self.assertEqual(settle(self.ledger,self.meta,self.now,self.reader)[0],0)
        self.assertIsNone(summarize(self.ledger)["markets"]["over15"]["models"]["candidate"]["accuracyPct"])
        self.payload["events"][0]["competitions"][0]["status"]["type"]["completed"]=True
        self.csv=self.csv.replace(b",2,1",b",3,1")
        self.assertEqual(settle(self.ledger,self.meta,self.now,self.reader)[0],0)
        self.assertEqual(summarize(self.ledger)["quarantined"],1)
    def test_wrong_id_and_duplicate(self):
        self.payload["events"][0]["id"]="456"
        self.assertEqual(settle(self.ledger,self.meta,self.now,self.reader)[0],0)
        self.payload["events"][0]["id"]="123"
        self.csv+=b"29/11/2026,Hearts,Celtic,2,1\n"
        settle(self.ledger,self.meta,self.now,self.reader)
        self.assertEqual(summarize(self.ledger)["quarantined"],1)
    def test_diagnostics_and_malformed_source(self):
        d={}
        self.payload["events"][0]["competitions"][0]["status"]["type"]["completed"]=False
        self.assertEqual(settle(self.ledger,self.meta,self.now,self.reader,diagnostics=d)[0],0)
        self.assertEqual(d["counts"],{"espn_final_score_missing":1})
        self.assertEqual(d["classifiedFixtures"],1)
        self.assertEqual(d["uniqueCSVRequests"],1)
        self.assertEqual(d["uniqueESPNRequests"],1)
        self.payload={"unexpected":[]}
        d={}
        added,errors=settle(self.ledger,self.meta,self.now,self.reader,diagnostics=d)
        self.assertEqual(added,0)
        self.assertEqual(d["counts"],{"espn_source_unavailable":1})
        self.assertEqual(errors[0]["source"],"espn")
        self.assertEqual(summarize(self.ledger)["quarantined"],0)
        self.assertEqual(summarize(self.ledger)["pending"],1)
    def test_revised_score_when_other_source_unavailable(self):
        for unavailable in ("csv","espn"):
            with self.subTest(unavailable=unavailable):
                self.setUp()
                self.assertEqual(settle(self.ledger,self.meta,self.now,self.reader)[0],1)
                original=copy.deepcopy(self.ledger["settlements"])
                forecasts=copy.deepcopy(self.ledger["forecasts"])
                if unavailable=="csv":
                    self.payload["events"][0]["competitions"][0]["competitors"][0]["score"]="3"
                else:
                    self.csv=self.csv.replace(b",2,1",b",3,1")
                def partial(url):
                    if ("football-data" in url)==(unavailable=="csv"):
                        raise OSError("source offline")
                    return self.reader(url)
                d={}
                added,errors=settle(self.ledger,self.meta,self.now,partial,diagnostics=d)
                self.assertEqual(added,0)
                self.assertEqual(len(errors),1)
                self.assertEqual(d["counts"],{"settled_score_changed":1})
                self.assertEqual(summarize(self.ledger)["validSettled"],0)
                self.assertEqual(summarize(self.ledger)["quarantined"],1)
                self.assertEqual(self.ledger["settlements"],original)
                self.assertEqual(self.ledger["forecasts"],forecasts)
    def test_partial_source_does_not_settle_or_quarantine_unchanged_score(self):
        def partial(url):
            if "football-data" in url:
                raise OSError("source offline")
            return self.reader(url)
        d={}
        self.assertEqual(settle(self.ledger,self.meta,self.now,partial,diagnostics=d)[0],0)
        self.assertEqual(d["counts"],{"csv_source_unavailable":1})
        self.assertEqual(summarize(self.ledger)["pending"],1)
        self.assertEqual(settle(self.ledger,self.meta,self.now,self.reader)[0],1)
        d={}
        self.assertEqual(settle(self.ledger,self.meta,self.now,partial,diagnostics=d)[0],0)
        self.assertEqual(d["counts"],{"previously_verified_csv_source_unavailable":1})
        self.assertEqual(summarize(self.ledger)["validSettled"],1)
        self.assertEqual(summarize(self.ledger)["quarantined"],0)
if __name__=="__main__":
    unittest.main()
