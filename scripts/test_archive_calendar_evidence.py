import copy
import unittest
from datetime import datetime,timezone,timedelta
from archive_calendar_evidence import capture

class EvidenceTests(unittest.TestCase):
    def test_immutable_pre_kickoff_capture(self):
        now=datetime(2026,11,26,14,tzinfo=timezone.utc)
        ts=now.isoformat()
        daily={"updatedAt":ts}
        odds={"updatedAt":ts,"events":[{"id":"one","league":"soccer_epl","home":"Arsenal","away":"Manchester City","kickoff":"2026-11-27T19:00:00Z"}]}
        cal={"status":"research_only","oddsFresh":True,"dailyUpdatedAt":ts,"oddsUpdatedAt":ts,"updatedAt":ts,"proposedCorrections":[{"league":"İngiltere Premier Lig","match":"Arsenal FC – Manchester City FC","originalDate":"2026-11-28","corroboratedDate":"2026-11-27","eventId":"one"}]}
        rec={"league":"en.1","home":"Arsenal FC","away":"Manchester City FC","date":"2026-11-28","recordedAt":"2026-11-25T18:00:00Z","result":None,"candidate":.7}
        archives={"prospective":{"a":rec}}
        before=copy.deepcopy(archives)
        ledger,status=capture({},archives,cal,daily,odds,now)
        self.assertEqual(status["newObservations"],1)
        self.assertEqual(archives,before)
        self.assertEqual(capture(ledger,archives,cal,daily,odds,now)[0],ledger)
        self.assertEqual(capture({},archives,cal,daily,odds,now+timedelta(minutes=31))[0],{})
        changed=copy.deepcopy(odds)
        changed["events"][0]["kickoff"]="2026-11-27T20:00:00Z"
        second,status=capture(ledger,archives,cal,daily,changed,now)
        self.assertEqual(len(second),2)
        self.assertEqual(status["multipleScheduleObservations"],1)
        self.assertEqual(len(ledger),1)
        after=datetime(2026,11,27,20,tzinfo=timezone.utc)
        newts=after.isoformat()
        self.assertEqual(capture({},archives,dict(cal,updatedAt=newts,dailyUpdatedAt=newts,oddsUpdatedAt=newts),dict(daily,updatedAt=newts),dict(odds,updatedAt=newts),after)[0],{})
if __name__=="__main__": unittest.main()
