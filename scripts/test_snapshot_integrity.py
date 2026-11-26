import copy
import unittest
from snapshot_integrity import audit

class SnapshotTests(unittest.TestCase):
    def test_integrity(self):
        ident=dict(archive="prospective",league="en.1",home="A",away="B",archivedDate="2026-11-28",recordedAt="2026-11-25T10:00:00Z")
        data={
            "daily":dict(candidateCount=1,candidates=[{}],upcomingCount=1,upcoming=[{}]),
            "odds":dict(eventCount=1,events=[{}]),
            "matching":dict(matchedCount=1,matched=[{}],unmatchedCount=0,unmatched=[]),
            "prospective_archive":{"a":{"result":None}},
            "prospective_validation":dict(recorded=1,tested=0,pending=1,liveEnabled=False),
            "prediction_archive":{"a":{"result":None}},
            "performance":{"overall":dict(recorded=1,settled=0,pending=1,markets={"2.5":{"tested":0}})},
            "data_quality":dict(archiveRecords=1,settled=0,pending=1),
            "archive_calendar_evidence":{"a":ident},
            "archive_calendar_evidence_status":dict(observations=1,archiveIdentities=1),
            "archive_calendar_result_replay":dict(rows=[dict(ident,status="awaiting_match")],counts={"awaiting_match":1}),
            "score_provenance":dict(version="4.80",settledArchiveRecords=0,uniqueSettledMatches=0,rows=[],counts={"prospective":{},"performance":{}}),
            "multi_league_results":dict(version="4.69"),
            "fixture_reconciliation":dict(status="unavailable"),
            "unified_decision":dict(testedMatches=0,decision="PAS",realBettingEnabled=False,selections=[]),
        }
        data["daily"]["updatedAt"]="2026-11-26T14:00:00Z"
        self.assertEqual(audit(data)["status"],"PASS")
        self.assertEqual(audit(data)["reportTimestamps"],{"daily.json":"2026-11-26T14:00:00Z"})
        for section,field,value,label in [
            ("daily","candidateCount",2,"candidate_count"),
            ("score_provenance","settledArchiveRecords",1,"score_provenance_identity"),
            ("score_provenance","uniqueSettledMatches",1,"score_provenance_unique_count"),
            ("multi_league_results","version","wrong","score_report_version"),
            ("prospective_validation","tested",1,"prospective_count"),
            ("archive_calendar_evidence_status","observations",2,"evidence_count"),
            ("archive_calendar_result_replay","counts",{},"calendar_replay_count"),
            ("unified_decision","realBettingEnabled",True,"research_lock"),
        ]:
            bad=copy.deepcopy(data);bad[section][field]=value
            self.assertIn(label,audit(bad)["errors"])
        self.assertEqual(audit({})["status"],"FAIL")
if __name__=="__main__": unittest.main()
