import unittest
from datetime import datetime, timezone, timedelta
from fixture_reconciliation import reconcile, parse_csv

class ReconcileTests(unittest.TestCase):
    def test_two_feeds_and_guards(self):
        now=datetime(2026,11,26,13,tzinfo=timezone.utc)
        league="soccer_epl"
        daily={"candidates":[{"date":"2026-11-28","league":"İngiltere Premier Lig","match":"Everton FC – Liverpool FC"}]}
        event=dict(id="one",league=league,home="Everton",away="Liverpool",kickoff="2026-11-29T12:00:00Z")
        odds=dict(updatedAt=now.isoformat(),source="The Odds API",region="uk",errors=[],queriedLeagues=[league],events=[event])
        cal={league:[dict(date="2026-11-29",home="Everton",away="Liverpool")]}
        stamp=now.isoformat()
        out=reconcile(daily,odds,cal,now,stamp)
        self.assertEqual(out["originalMatched"],0)
        self.assertEqual(out["reconciledMatched"],1)
        self.assertEqual(len(out["proposedCorrections"]),1)
        self.assertEqual(daily["candidates"][0]["date"],"2026-11-28")
        self.assertEqual(out["decision"],"PAS")
        self.assertEqual(reconcile(daily,odds,cal,now+timedelta(minutes=31),stamp)["proposedCorrections"],[])
        self.assertEqual(reconcile(daily,odds,{league:cal[league]*2},now,stamp)["proposedCorrections"],[])
        self.assertEqual(reconcile(daily,dict(odds,events=[event,dict(event,id="two")]),cal,now,stamp)["proposedCorrections"],[])
        self.assertEqual(reconcile(daily,odds,{league:[dict(cal[league][0],date="2026-11-28")]},now,stamp)["proposedCorrections"],[])
    def test_csv(self):
        self.assertEqual(parse_csv(b"date,home,away\n2026-11-29,A,B\n"),[dict(date="2026-11-29",home="A",away="B")])

if __name__=="__main__": unittest.main()
