import copy
import unittest
from datetime import datetime,timedelta
from archive_calendar_outcomes import collect,TR
from multi_league_results import source_urls

class OutcomeTests(unittest.TestCase):
    def test_capture_and_retention(self):
        now=datetime(2026,11,30,18,tzinfo=TR)
        rec=dict(league="en.1",date="2026-11-28",home="A",away="B",recordedAt="2026-11-24T10:00:00Z",old=.6,candidate=.7,baseline=.5,result=None)
        archives={"prospective":{"r":rec},"performance":{}}
        row=dict(archive="prospective",league="en.1",home="A",away="B",archivedDate=rec["date"],recordedAt=rec["recordedAt"],eventId="event",corroboratedDate="2026-11-29",kickoff="2026-11-29T14:00:00Z",status="research_score_verified",csv=[2,1],espn=[2,1],sources=list(source_urls("en.1","2026-11-29")))
        replay=dict(version="4.72",mode="research_only",updatedAt=now.isoformat(),rows=[row])
        original=copy.deepcopy(archives)
        ledger,out=collect({},replay,archives,now)
        self.assertEqual(out["newObservations"],1)
        self.assertEqual(out["uniqueEligibleEvents"],1)
        self.assertAlmostEqual(out["metrics"]["prospective"]["candidate"]["brier"],.09)
        self.assertEqual(archives,original)
        self.assertFalse(out["includedInMainValidation"])
        self.assertEqual(collect(ledger,replay,archives,now)[1]["newObservations"],0)
        self.assertEqual(collect({},replay,archives,now+timedelta(hours=1))[1]["observations"],0)
        self.assertEqual(collect(ledger,{},archives,now+timedelta(days=20))[1]["uniqueEligibleEvents"],1)
        conflict=copy.deepcopy(replay);conflict["rows"][0]["status"]="conflict"
        self.assertEqual(collect(ledger,conflict,archives,now)[1]["counts"],{"current_conflict":1})
        revised=copy.deepcopy(replay);revised["rows"][0].update(csv=[1,1],espn=[1,1])
        _,out=collect(ledger,revised,archives,now)
        self.assertEqual(out["counts"],{"conflicting_observations":1})
        self.assertEqual(out["uniqueEligibleEvents"],0)
        rec["result"]=[2,1]
        self.assertEqual(collect(ledger,replay,archives,now)[1]["counts"],{"excluded_archive_state":1})
if __name__=="__main__": unittest.main()
