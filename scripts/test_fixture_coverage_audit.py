import unittest,copy
from datetime import datetime
from fixture_coverage_audit import compare,TR
class CoverageTests(unittest.TestCase):
    def test_comparison(self):
        now=datetime(2026,11,26,19,tzinfo=TR)
        daily={"updatedAt":now.isoformat(),"upcoming":[{"date":"2026-11-27","league":"İngiltere Premier Lig","match":"A – B"},{"date":"2026-11-27","league":"İngiltere Premier Lig","match":"C – D"}]}
        def board(day,rows,error=None):
            return {"date":day,"groups":[{"league":"en.1","error":error,"invalid":0,"rows":rows}]}
        def event(h,a,i,day):
            return dict(home=h,away=a,eventId=i,kickoff=day+"T18:00:00Z",state="pre",status="STATUS_SCHEDULED")
        boards=[board("2026-11-27",[event("A","B","1","2026-11-27")]),board("2026-11-28",[event("C","D","2","2026-11-28"),event("E","F","3","2026-11-28")])]
        original=copy.deepcopy(daily)
        r=compare(daily,boards,now)
        self.assertEqual(r["counts"],{"same_date":1,"date_difference":1,"espn_only":1})
        self.assertEqual(daily,original)
        self.assertFalse(r["archivesModified"])
        boards[1]["groups"][0]["error"]="offline"
        self.assertEqual(compare(daily,boards,now)["counts"],{"source_incomplete":2})
if __name__=="__main__":unittest.main()
