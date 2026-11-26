import unittest
from datetime import datetime
from calendar_duplicate_guard import blocked_dates,TR

class DuplicateGuardTests(unittest.TestCase):
    def test_pre_kickoff_evidence_only(self):
        now=datetime(2026,11,27,17,tzinfo=TR)
        record=dict(league="en.1",home="A",away="B",date="2026-11-28",recordedAt="2026-11-24T18:00:00Z",result=None)
        e=dict(archive="prospective",league="en.1",home="A",away="B",archivedDate="2026-11-28",recordedAt=record["recordedAt"],eventId="abc",corroboratedDate="2026-11-29",kickoff="2026-11-29T16:30:00Z",observedAt="2026-11-26T14:00:00Z",status="review_pending")
        records={"a":record}
        expected={("en.1","A","B","2026-11-29")}
        self.assertEqual(blocked_dates({"e":e},records,"prospective",now),expected)
        self.assertEqual(blocked_dates({},records,"prospective",now),set())
        self.assertEqual(blocked_dates({"e":e},{}, "prospective",now),set())
        self.assertEqual(blocked_dates({"e":dict(e,observedAt="2026-11-30T14:00:00Z")},records,"prospective",now),set())
        self.assertEqual(blocked_dates({"e":dict(e,recordedAt="2026-11-23T18:00:00Z")},records,"prospective",now),set())
        self.assertEqual(blocked_dates({"e":dict(e,eventId="")},records,"prospective",now),set())
        self.assertEqual(blocked_dates({"e":dict(e,corroboratedDate="2026-11-30")},records,"prospective",now),set())
        perf={"a":dict(league="İngiltere Premier Lig",match="A – B",date=record["date"],recordedAt=record["recordedAt"],result=None)}
        self.assertEqual(blocked_dates({"e":dict(e,archive="performance")},perf,"performance",now),expected)
        self.assertEqual(record["result"],None)
if __name__=="__main__": unittest.main()
