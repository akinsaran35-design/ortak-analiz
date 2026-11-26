import json
import unittest
from datetime import datetime
from archive_calendar_result_replay import replay,TR

class ReplayTests(unittest.TestCase):
    def test_replay(self):
        now=datetime(2026,11,30,17,tzinfo=TR)
        rec=dict(league="en.1",home="Arsenal FC",away="Manchester City FC",date="2026-11-28",recordedAt="2026-11-24T18:00:00+03:00",result=None,candidate=.6)
        e=dict(archive="prospective",league=rec["league"],home=rec["home"],away=rec["away"],archivedDate=rec["date"],recordedAt=rec["recordedAt"],eventId="abc",corroboratedDate="2026-11-29",kickoff="2026-11-29T16:30:00+00:00",observedAt="2026-11-26T14:00:00+00:00",status="review_pending")
        event={"date":"2026-11-29T16:30:00Z","competitions":[{"status":{"type":{"completed":True,"name":"STATUS_FULL_TIME"}},"competitors":[{"homeAway":"home","team":{"displayName":"Arsenal"},"score":"2"},{"homeAway":"away","team":{"displayName":"Manchester City"},"score":"1"}]}]}
        def read(url):
            if url.endswith("/E0.csv"): return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n29/11/26,Arsenal,Manchester City,2,1\n"
            return json.dumps({"events":[event]}).encode()
        a={"prospective":{"a":rec}}
        self.assertEqual(replay({"e":e},a,now,read)["counts"],{"research_score_verified":1})
        self.assertIsNone(rec["result"])
        self.assertEqual(replay({"e":e},a,datetime(2026,11,27,17,tzinfo=TR),read)["counts"],{"awaiting_match":1})
        self.assertEqual(replay({"e":e,"f":dict(e,eventId="other")},a,now,read)["counts"],{"schedule_conflict":1})
        self.assertEqual(replay({"e":e},{"prospective":{"a":rec,"b":dict(rec,date="2026-11-29")}},now,read)["counts"],{"duplicate_risk":1})
        event["competitions"][0]["competitors"][0]["score"]="3"
        self.assertEqual(replay({"e":e},a,now,read)["counts"],{"conflict":1})
if __name__=="__main__": unittest.main()
