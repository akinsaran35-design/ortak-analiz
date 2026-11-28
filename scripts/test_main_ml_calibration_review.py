import unittest,copy
from datetime import datetime
from main_ml_calibration_review import evaluate,dual_gate
from main_ml_matched_comparison import build,identity
from extra_league_prospective import key
import json
from results_source_pilot import TR
class ReviewTests(unittest.TestCase):
    def test_empty_never_approved(self):
        meta=dict(modelSha256="test",frozenAt="2026-11-28T09:00:00+03:00")
        ledger=dict(version="6.67",modelSha256="test",forecasts={},settlements={},quarantine={})
        pairs=dict(version="6.69",modelSha256="test",pairs={})
        before=copy.deepcopy((ledger,pairs))
        r=evaluate(pairs,ledger,meta,datetime(2026,11,28,12,tzinfo=TR))
        self.assertFalse(r["automaticApproval"])
        self.assertFalse(r["overall"]["reviewScreenReady"])
        self.assertFalse(r["overall"]["legacyProvenanceReady"])
        self.assertFalse(r["legacySourceAvailable"])
        self.assertFalse(r["overall"]["sameCalendarCutoffScreen"]["descriptiveScreenReady"])
        self.assertFalse(r["sameInformationCutoffEstablished"])
        self.assertEqual(len(r["leagues"]),9)
        self.assertTrue(all(v["status"]=="collecting_data" for v in r["leagues"].values()))
        self.assertEqual((ledger,pairs),before)
        self.assertTrue(all(v["gate"]["status"]=="not_evaluated" for v in r["overall"]["markets"].values()))
    def test_wrong_cohort(self):
        with self.assertRaises(ValueError):
            evaluate(dict(version="6.69",modelSha256="bad",pairs={}),dict(version="6.67",modelSha256="x",forecasts={},settlements={},quarantine={}),dict(modelSha256="x"),datetime(2026,11,28,12,tzinfo=TR))
    def test_both_baselines_required(self):
        def metric(brier,loss):
            return dict(brier=brier,logLoss=loss,ece10=.02,bins=[dict(n=100)])
        candidate=metric(.15,.4)
        row=dict(candidate=candidate,legacy=metric(.18,.5),poisson=metric(.14,.39),
            pairedBootstrap=dict(interval95=[.01,.04]),pairedPoissonBootstrap=dict(interval95=[-.02,-.001]))
        self.assertEqual(dual_gate(row,False)["status"],"not_evaluated")
        r=dual_gate(row,True)
        self.assertTrue(r["checks"]["legacyPass"])
        self.assertFalse(r["checks"]["poissonPass"])
        self.assertEqual(r["status"],"retain_baseline")
        row["poisson"]=metric(.17,.5)
        row["pairedPoissonBootstrap"]=dict(interval95=[.01,.03])
        self.assertEqual(dual_gate(row,True)["status"],"eligible_for_manual_review")
    def test_documented_cutoff_is_separate_and_insufficient(self):
        p=dict(over15=.8,over25=.6,btts=.5)
        f=dict(league="en.1",date="2026-11-29",home=identity("en.1","Manchester United"),away=identity("en.1","Liverpool"),eventId="123",kickoff="2026-11-29T12:00:00+00:00",recordedAt="2026-11-28T11:00:00+03:00",historyThrough="2026-11-27",policyVersion="6.67",modelSha256="x",poisson=p,catboost=p,candidate=p)
        k=key(f)
        ledger=dict(version="6.67",modelSha256="x",forecasts={k:f},settlements={},quarantine={})
        meta=dict(modelSha256="x",frozenAt="2026-11-28T09:00:00+03:00")
        timing=dict(version="6.82",generationStartedAt="2026-11-28T09:00:00+03:00",generationCompletedAt="2026-11-28T09:30:00+03:00",historyCutoffExclusive="2026-11-28",historyThrough="2026-11-27",sameSourceDataEstablished=False)
        old=dict(date=f["date"],league="İngiltere Premier Lig",match="Man United – Liverpool",recordedAt="2026-11-28T10:00:00+03:00",modelVersion="1.6",markets={"1.5 Üst":80,"2.5 Üst":60,"KG Var":50},result=None,forecastTiming=timing)
        lk=json.dumps([old["date"],old["league"],old["match"]],ensure_ascii=False)
        legacy={lk:old}
        pairs=dict(version="6.69",modelSha256="x",pairs={})
        build(pairs,ledger,meta,legacy,datetime(2026,11,28,12,tzinfo=TR))
        ledger["settlements"][k]=dict(eventId="123",sources=["espn","football-data"],score=[2,1],settledAt="2026-11-30T12:00:00+03:00")
        now=datetime(2026,12,7,12,tzinfo=TR)
        before=copy.deepcopy((pairs,ledger,legacy))
        r=evaluate(pairs,ledger,meta,now,legacy)
        screen=r["overall"]["sameCalendarCutoffScreen"]
        self.assertEqual(screen["sameCutoffPairs"],1)
        self.assertEqual(screen["validSettled"],1)
        self.assertEqual(screen["matureSameCutoffShareAmongDocumentedPairs"],1)
        self.assertTrue(screen["checks"]["legacyProvenance"])
        self.assertFalse(screen["checks"]["sample"])
        self.assertFalse(screen["descriptiveScreenReady"])
        self.assertFalse(screen["sameSourceDataEstablished"])
        self.assertEqual(screen["markets"]["over15"]["status"],"not_evaluated")
        self.assertEqual(r["leagues"]["en.1"]["sameCalendarCutoffScreen"]["validSettled"],1)
        self.assertEqual((pairs,ledger,legacy),before)
        self.assertFalse(evaluate(pairs,ledger,meta,now,{})["overall"]["sameCalendarCutoffScreen"]["checks"]["legacyProvenance"])
if __name__=="__main__":unittest.main()
