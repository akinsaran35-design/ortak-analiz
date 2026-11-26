import json
import unittest
from datetime import datetime,timedelta
from live_refresh_snapshot import build,is_fresh
from results_source_pilot import TR

NOW=datetime(2026,11,26,20,0,tzinfo=TR)
ROW=dict(eventId="123",home="A",away="B",kickoff="2026-11-26T16:00:00+00:00",state="in")
def board_with(rows):
    def board(now,reader,query_date):
        return {"groups":[dict(league="en.1",error=None,invalid=0,rows=rows if query_date==NOW.date().isoformat() else [])]}
    return board
def summary(state="in"):
    comp=dict(id="123",date=ROW["kickoff"],status={"type":{"state":state,"name":"STATUS_IN_PROGRESS" if state=="in" else "STATUS_FULL_TIME"},"displayClock":"54'"},competitors=[{"homeAway":"home","team":{"id":"1","displayName":"A"},"score":"2"},{"homeAway":"away","team":{"id":"2","displayName":"B"},"score":"1"}])
    return json.dumps({"header":{"competitions":[comp]}}).encode()

class Tests(unittest.TestCase):
    def test_freshness(self):
        self.assertTrue(is_fresh(NOW.isoformat(),NOW))
        self.assertTrue(is_fresh((NOW-timedelta(seconds=120)).isoformat(),NOW))
        self.assertFalse(is_fresh((NOW-timedelta(seconds=121)).isoformat(),NOW))
        self.assertFalse(is_fresh((NOW+timedelta(seconds=1)).isoformat(),NOW))
        self.assertFalse(is_fresh("invalid",NOW))
        self.assertFalse(is_fresh("2026-11-26T20:00:00",NOW))
    def test_live_only(self):
        calls=[]
        def reader(url):calls.append(url);return summary()
        r=build(NOW,reader,board_with([ROW,dict(ROW,eventId="124",state="post")]),clock=lambda:NOW)
        self.assertEqual(r["requested"],1)
        self.assertEqual(r["freshAtBuild"],1)
        self.assertEqual(len(calls),1)
        self.assertFalse(r["sourceTimestampVerified"])
        self.assertFalse(r["predictionsEnabled"])
    def test_no_live_and_finished(self):
        r=build(NOW,lambda url:self.fail("unexpected summary request"),board_with([]),clock=lambda:NOW)
        self.assertEqual(r["requested"],0)
        r=build(NOW,lambda url:summary("post"),board_with([ROW]),clock=lambda:NOW)
        self.assertEqual(r["freshAtBuild"],0)
        self.assertIsNone(r["rows"][0]["observation"])
    def test_source_failure(self):
        def reader(url):raise OSError("unavailable")
        r=build(NOW,reader,board_with([ROW]),clock=lambda:NOW)
        self.assertEqual(r["freshAtBuild"],0)
        self.assertEqual(r["rows"][0]["error"],"OSError")
if __name__=="__main__":unittest.main()
