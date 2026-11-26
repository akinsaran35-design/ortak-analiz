import copy
import unittest
from snapshot_integrity import audit

class SnapshotTests(unittest.TestCase):
    def test_integrity(self):
        ident=dict(archive="prospective",league="en.1",home="A",away="B",archivedDate="2026-11-28",recordedAt="2026-11-25T10:00:00Z")
        data={
            "daily":dict(candidateCount=1,candidates=[{}],upcomingCount=1,upcoming=[{"date":"2026-11-27","league":"İngiltere Premier Lig","match":"A – B"}]),
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
            "archive_calendar_outcomes":{},
            "archive_calendar_outcome_status":dict(version="4.83",observations=0,conflictObservations=0,archiveIdentities=0,quarantinedIdentities=0,counts={},uniqueEligibleEvents=0,includedInMainValidation=False,decision="PAS"),
            "unified_decision":dict(testedMatches=0,decision="PAS",realBettingEnabled=False,selections=[]),
        }
        from datetime import datetime
        from prospective_markets import summarize
        data["prospective_validation"]["updatedAt"]="2026-11-26T14:00:00Z"
        data["prospective_validation"]["marketResearchVersion"]="4.85"
        from prospective_leagues import build
        data["prospective_archive"]["a"].update(league="en.1")
        data["prospective_leagues"]=build(data["prospective_archive"],datetime.fromisoformat("2026-11-26T14:00:00Z"))
        data["prospective_validation"]["marketResearch"]=summarize(data["prospective_archive"],datetime.fromisoformat("2026-11-26T14:00:00Z"))
        data["daily"]["updatedAt"]="2026-11-26T14:00:00Z"
        from league_config import FIXTURE_CODES
        data["scoreboard_snapshot"]=dict(version="4.90",mode="scoreboard_snapshot",updatedAt="2026-11-26T14:00:00Z",date="2026-11-26",realTime=False,usedForSettlement=False,usedForPredictions=False,groups=[dict(league=x,rows=[],error=None) for x in FIXTURE_CODES.values()],loadedLeagues=9,eventCount=0,inProgress=0)
        data["fixture_coverage_audit"]=dict(version="4.92",mode="research_only",updatedAt="2026-11-26T14:00:00Z",dailyUpdatedAt=data["daily"]["updatedAt"],archivesModified=False,decision="PAS",dates=["2026-11-27","2026-11-28","2026-11-29"],sourceGroups=27,healthyGroups=27,counts={"published_only":1},rows=[dict(league="en.1",status="published_only",published=data["daily"]["upcoming"],espn=[])])
        self.assertEqual(audit(data)["status"],"PASS")
        self.assertEqual(audit(data)["reportTimestamps"],{"daily.json":"2026-11-26T14:00:00Z","prospective_validation.json":"2026-11-26T14:00:00Z","prospective_leagues.json":"2026-11-26T14:00:00+00:00","scoreboard_snapshot.json":"2026-11-26T14:00:00Z","fixture_coverage_audit.json":"2026-11-26T14:00:00Z"})
        for section,field,value,label in [
            ("daily","candidateCount",2,"candidate_count"),
            ("scoreboard_snapshot","eventCount",1,"scoreboard_counts"),
            ("scoreboard_snapshot","usedForPredictions",True,"scoreboard_lock"),
            ("fixture_coverage_audit","counts",{},"fixture_audit_counts"),
            ("fixture_coverage_audit","dailyUpdatedAt","wrong","fixture_audit_lock"),
            ("prospective_leagues","recorded",2,"prospective_league_recompute"),
            ("prospective_validation","marketResearch",{},"prospective_market_recompute"),
            ("archive_calendar_outcome_status","conflictObservations",1,"outcome_observation_count"),
            ("archive_calendar_outcome_status","includedInMainValidation",True,"outcome_research_lock"),
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
