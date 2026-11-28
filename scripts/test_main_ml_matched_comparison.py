import copy,json,unittest
from datetime import datetime
from main_ml_matched_comparison import build,identity
from results_source_pilot import TR
from extra_league_prospective import key
class MatchedTests(unittest.TestCase):
    def test_lock_and_no_late_pairing(self):
        probs=dict(over15=.8,over25=.6,btts=.5)
        f=dict(league="en.1",date="2026-11-29",home=identity("en.1","Manchester United"),away=identity("en.1","Liverpool"),eventId="123",kickoff="2026-11-29T12:00:00+00:00",recordedAt="2026-11-28T11:00:00+03:00",historyThrough="2026-11-27",policyVersion="6.67",modelSha256="x",poisson=probs,catboost=probs,candidate=probs)
        k=key(f)
        ledger=dict(version="6.67",modelSha256="x",forecasts={k:f},settlements={},quarantine={})
        meta=dict(modelSha256="x",frozenAt="2026-11-28T10:00:00+03:00")
        old=dict(date=f["date"],league="İngiltere Premier Lig",match="Man United – Liverpool",recordedAt="2026-11-27T12:00:00+03:00",modelVersion="1.6",markets={"1.5 Üst":80,"2.5 Üst":60,"KG Var":50},result=None)
        lk=json.dumps([old["date"],old["league"],old["match"]],ensure_ascii=False)
        legacy={lk:old}
        pairs=dict(version="6.69",modelSha256="x",pairs={})
        now=datetime(2026,11,28,12,tzinfo=TR)
        self.assertEqual(build(pairs,ledger,meta,legacy,now)["newPairs"],1)
        frozen=copy.deepcopy(pairs)
        self.assertEqual(build(pairs,ledger,meta,legacy,now)["newPairs"],0)
        self.assertEqual(pairs,frozen)
        end=datetime(2026,12,1,12,tzinfo=TR)
        ledger["settlements"][k]=dict(eventId="123",sources=["espn","football-data"],score=[2,1],settledAt="2026-11-30T12:00:00+03:00")
        self.assertEqual(build(pairs,ledger,meta,legacy,end)["validSettled"],1)
        empty=dict(version="6.69",modelSha256="x",pairs={})
        self.assertEqual(build(empty,ledger,meta,legacy,end)["paired"],0)
        self.assertEqual(build(pairs,ledger,meta,legacy,end)["markets"]["over15"]["candidate"]["n"],1)
        stats=build(pairs,ledger,meta,legacy,end)["markets"]["over15"]
        self.assertEqual(stats["poisson"]["n"],stats["legacy"]["n"])
        self.assertEqual(stats["poisson"]["n"],stats["candidate"]["n"])
        self.assertTrue(stats["identicalEvaluationSample"])
        self.assertEqual(stats["pairedPoissonBootstrap"]["meanImprovement"],0)
        ledger["quarantine"][k]={}
        self.assertEqual(build(pairs,ledger,meta,legacy,end)["validSettled"],0)
if __name__=="__main__":unittest.main()
