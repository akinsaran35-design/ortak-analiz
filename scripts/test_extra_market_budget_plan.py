import unittest
from datetime import datetime,timezone,timedelta
from extra_market_budget_plan import plan,scheduled_slots
from league_config import ODDS_CODES

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,28,9,25,tzinfo=timezone.utc)
        self.stamp=self.now-timedelta(minutes=4)
        self.workflow="    - cron: '0 5,15 * * *'\n    - cron: '10 8,11,13,18 * * 6,0'\n"
        self.s=dict(source="The Odds API",region="uk",market="totals",errors=[],
            configuredLeagues=list(ODDS_CODES.values()),updatedAt=self.stamp.isoformat(),remainingCredits=80)
    def test_weekend_reserve(self):
        r=plan(self.s,self.now,self.workflow)
        self.assertEqual(r["scheduledRunsRemaining"],12)
        self.assertEqual(r["baseCreditsReserved"],108)
        self.assertEqual(r["totalCreditsReserved"],128)
        self.assertEqual(r["reserveShortfall"],48)
        self.assertEqual(r["theoreticalExtraEventCapacity"],0)
        self.assertFalse(r["collectionEnabled"])
    def test_high_balance_and_stale(self):
        s=dict(self.s,remainingCredits=500)
        self.assertEqual(plan(s,self.now,self.workflow)["theoreticalExtraEventCapacity"],3)
        self.assertIsNone(plan(s,self.now+timedelta(hours=1),self.workflow)["theoreticalExtraEventCapacity"])
    def test_fail_closed(self):
        for s in (dict(self.s,remainingCredits=True),dict(self.s,remainingCredits=None),
                  dict(self.s,updatedAt="2026-11-28T09:21:00"),dict(self.s,region="tr")):
            self.assertEqual(plan(s,self.now,self.workflow)["status"],"invalid_snapshot")
        self.assertEqual(plan(self.s,self.now,self.workflow+"    - cron: '0 12 * * *'\n")["status"],"schedule_changed")
    def test_month_end(self):
        self.assertEqual(scheduled_slots(datetime(2026,12,31,16,tzinfo=timezone.utc)),[])
        self.assertEqual(len(scheduled_slots(datetime(2026,11,29,16,tzinfo=timezone.utc))),3)
if __name__=="__main__":unittest.main()
