import unittest,json
from datetime import datetime
from scoreboard_snapshot import parse,build,TR
def event(state="in",name="STATUS_IN_PROGRESS",completed=False):
    return {"id":"123","date":"2026-11-28T15:00:00Z","competitions":[{"date":"2026-11-28T15:00:00Z","status":{"type":{"state":state,"name":name,"completed":completed},"displayClock":"54'"},"competitors":[{"homeAway":"home","team":{"displayName":"A"},"score":"2"},{"homeAway":"away","team":{"displayName":"B"},"score":"1"}]}]}
class SnapshotTests(unittest.TestCase):
    def test_parse(self):
        e=event()
        rows,bad=parse({"events":[e]},"2026-11-28")
        self.assertEqual(rows[0]["score"],[2,1]);self.assertEqual(bad,0)
        self.assertIsNone(parse({"events":[event("pre","STATUS_SCHEDULED")]},"2026-11-28")[0][0]["score"])
        self.assertEqual(parse({"events":[e]},"2026-11-29"),([],0))
        self.assertEqual(parse({"events":[e,event("pre","STATUS_SCHEDULED")]},"2026-11-28"),([],1))
        self.assertEqual(parse({"events":[{}]},"2026-11-28"),([],1))
    def test_snapshot(self):
        def read(url):
            if "/eng.2/" in url: raise OSError("offline")
            return json.dumps({"events":[]}).encode()
        r=build(datetime(2026,11,28,18,tzinfo=TR),read)
        self.assertEqual(r["loadedLeagues"],8)
        self.assertEqual(r["eventCount"],0)
        self.assertFalse(r["realTime"]);self.assertFalse(r["usedForSettlement"])
if __name__=="__main__":unittest.main()
