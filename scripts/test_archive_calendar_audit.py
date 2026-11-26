import copy
import unittest
from datetime import datetime,timezone,timedelta
from archive_calendar_audit import audit

class AuditTests(unittest.TestCase):
    def test_date_change(self):
        now=datetime(2026,11,26,14,tzinfo=timezone.utc)
        ts=now.isoformat()
        daily={"updatedAt":ts}
        odds={"updatedAt":ts,"events":[{"id":"one","league":"soccer_epl","home":"Arsenal","away":"Manchester City","kickoff":"2026-11-27T19:00:00Z"}]}
        cal={"status":"research_only","oddsFresh":True,"dailyUpdatedAt":ts,"oddsUpdatedAt":ts,"updatedAt":ts,"proposedCorrections":[{"league":"İngiltere Premier Lig","match":"Arsenal FC – Manchester City FC","originalDate":"2026-11-28","corroboratedDate":"2026-11-27","eventId":"one"}]}
        rec={"league":"en.1","home":"Arsenal FC","away":"Manchester City FC","date":"2026-11-28","recordedAt":"2026-11-25T18:00:00Z","result":None,"candidate":.7}
        archive={"a":rec}
        before=copy.deepcopy(archive)
        self.assertEqual(audit(archive,cal,daily,odds,now)["counts"],{"review_pending":1})
        self.assertEqual(archive,before)
        self.assertEqual(audit(dict(archive,b=dict(rec,date="2026-11-27")),cal,daily,odds,now)["counts"],{"duplicate_risk":1})
        self.assertEqual(audit(archive,cal,daily,odds,now+timedelta(minutes=31))["status"],"unavailable")
        self.assertEqual(audit({"a":dict(rec,recordedAt="2026-11-28T00:00:00Z")},cal,daily,odds,now)["counts"],{"late_prediction":1})
        perf={"a":dict(rec,league="İngiltere Premier Lig",match="Arsenal FC – Manchester City FC")}
        self.assertEqual(audit(perf,cal,daily,odds,now,True)["counts"],{"review_pending":1})
        self.assertEqual(audit(archive,cal,daily,dict(odds,events=odds["events"]*2),now)["rows"],[])
if __name__=="__main__": unittest.main()
