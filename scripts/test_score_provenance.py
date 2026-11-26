import unittest
from datetime import datetime
from score_provenance import audit,TR
from multi_league_results import source_urls

class ProvenanceTests(unittest.TestCase):
    def test_audit(self):
        now=datetime(2026,11,26,18,tzinfo=TR)
        r=dict(league="en.2",date="2026-11-25",home="A",away="B",result=[2,1])
        p=dict(league="İngiltere Championship",date=r["date"],match="A – B",result=[2,1])
        feed=dict(version="4.69",updatedAt=now.isoformat(),groups=[dict(league="en.2",date=r["date"],sources=list(source_urls("en.2",r["date"])),errors=[],rows=[dict(date=r["date"],home="A",away="B",csv=[2,1],espn=[2,1],status="corroborated")])])
        archives={"prospective":{"a":r},"performance":{"a":p}}
        out=audit(archives,feed,now)
        self.assertEqual(out["uniqueSettledMatches"],1)
        self.assertEqual(out["settledArchiveRecords"],2)
        self.assertEqual(out["counts"]["prospective"],{"currently_corroborated":1})
        self.assertEqual(out["counts"]["performance"],{"currently_corroborated":1})
        self.assertEqual(out["crossArchiveConflicts"],[])
        p["result"]=[1,1]
        out=audit(archives,feed,now)
        self.assertEqual(out["counts"]["performance"],{"source_conflict":1})
        self.assertEqual(len(out["crossArchiveConflicts"]),1)
        r["resultSources"]=["https://a.example/1","https://a.example/2"]
        self.assertEqual(audit(archives,{},now)["counts"]["prospective"],{"single_recorded_domain":1})
        r["resultSources"].append("https://b.example/1")
        self.assertEqual(audit(archives,{},now)["counts"]["prospective"],{"multiple_recorded_domains":1})
        self.assertEqual(audit(archives,{},now)["counts"]["performance"],{"provenance_missing":1})
    def test_conflict_rows_not_hidden(self):
        now=datetime(2026,11,26,18,tzinfo=TR)
        r=dict(league="en.2",date="2026-11-25",home="A",away="B",result=[1,1])
        archives={"prospective":{"a":r}}
        row=dict(date=r["date"],home="A",away="B",csv=[2,1],espn=[2,1],status="archive_conflict")
        feed=dict(version="4.69",updatedAt=now.isoformat(),groups=[dict(league="en.2",date=r["date"],sources=list(source_urls("en.2",r["date"])),errors=[],rows=[row])])
        self.assertEqual(audit(archives,feed,now)["counts"]["prospective"],{"source_conflict":1})
        row.update(espn=[3,1],status="conflict")
        out=audit(archives,feed,now)
        self.assertEqual(out["counts"]["prospective"],{"feed_disagreement":1})
        self.assertEqual(out["feedDisagreements"],1)
        self.assertEqual(r["result"],[1,1])
        feed["groups"][0]["sources"]=["https://invalid.example"]
        self.assertEqual(audit(archives,feed,now)["counts"]["prospective"],{"provenance_missing":1})
if __name__=="__main__": unittest.main()
