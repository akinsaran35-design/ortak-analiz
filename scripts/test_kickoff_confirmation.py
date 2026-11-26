import unittest,copy
from datetime import datetime
from kickoff_confirmation import build,TR
class KickoffTests(unittest.TestCase):
    def test_agreement(self):
        now=datetime(2026,11,26,19,tzinfo=TR)
        stamp=now.isoformat()
        p=dict(date="2026-11-28",league="İngiltere Premier Lig",match="Arsenal FC – Manchester City FC")
        s=dict(date="2026-11-29",eventId="1",kickoff="2026-11-29T16:30:00Z",match="Arsenal – Manchester City")
        daily=dict(updatedAt=stamp,upcoming=[p])
        coverage=dict(version="4.92",updatedAt=stamp,dailyUpdatedAt=stamp,archivesModified=False,mode="research_only",rows=[dict(league="en.1",status="date_difference",published=[p],espn=[s])])
        e=dict(id="odds1",league="soccer_epl",home="Arsenal",away="Manchester City",kickoff="2026-11-29T16:30:00+00:00")
        odds=dict(updatedAt=stamp,source="The Odds API",region="uk",errors=[],queriedLeagues=["soccer_epl"],events=[e])
        original=copy.deepcopy([daily,coverage,odds])
        r=build(daily,coverage,odds,now)
        self.assertEqual(r["counts"],{"agreed":1})
        self.assertEqual(r["rows"][0]["oddsEventId"],"odds1")
        self.assertEqual([daily,coverage,odds],original)
        self.assertFalse(r["archivesModified"])
        self.assertEqual(build(daily,coverage,dict(odds,events=[dict(e,kickoff="2026-11-29T17:00:00Z")]),now)["counts"],{"time_difference":1})
        self.assertEqual(build(daily,coverage,dict(odds,events=[e,dict(e,id="2")]),now)["counts"],{"ambiguous":1})
        self.assertFalse(build(daily,coverage,dict(odds,updatedAt="2026-11-26T15:00:00Z"),now)["available"])
if __name__=="__main__":unittest.main()
