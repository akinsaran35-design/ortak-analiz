import json
import unittest
from datetime import datetime,timedelta
from multi_league_results import build_report,verified_rows,source_urls,TR,APPROVED
from verified_results import settle_verified

class MultiLeagueTests(unittest.TestCase):
    def test_scope_and_source_guards(self):
        now=datetime(2026,11,26,17,tzinfo=TR)
        d="2026-11-25"
        base=dict(date=d,home="A",away="B",recordedAt="2026-11-24T17:00:00+03:00",candidate=.6,result=None)
        archive={"de":dict(base,league="de.1"),"pt":dict(base,league="pt.1")}
        event={"date":"2026-11-25T18:00:00Z","competitions":[{"status":{"type":{"completed":True,"name":"STATUS_FULL_TIME"}},"competitors":[{"homeAway":"home","team":{"displayName":"A"},"score":"2"},{"homeAway":"away","team":{"displayName":"B"},"score":"1"}]}]}
        def reader(url):
            if url==source_urls("de.1",d)[0]: return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n25/11/26,A,B,2,1\n"
            if url==source_urls("pt.1",d)[0]: return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n25/11/26,A,B,0,2\n"
            self.assertIn(url,{source_urls("de.1",d)[1],source_urls("pt.1",d)[1]})
            return json.dumps({"events":[event]}).encode()
        report=build_report(archive,now,reader)
        rows=verified_rows(report,now)
        self.assertEqual(len(APPROVED),9)
        self.assertEqual(len(rows),1)
        self.assertEqual(settle_verified(archive,rows,now),1)
        self.assertEqual(archive["de"]["candidate"],.6)
        self.assertIsNone(archive["pt"]["result"])
        self.assertEqual(report["groups"][1]["rows"][0]["status"],"conflict")
        def matching_portugal(url):
            if url==source_urls("pt.1",d)[0]: return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n25/11/26,A,B,2,1\n"
            return reader(url)
        pt_report=build_report({"pt":archive["pt"]},now,matching_portugal)
        self.assertEqual(settle_verified(archive,verified_rows(pt_report,now),now),1)
        self.assertEqual(archive["pt"]["result"],[2,1])
        self.assertEqual(verified_rows(report,now+timedelta(minutes=31)),[])
        dup=build_report({"x":dict(base,league="de.1"),"y":dict(base,league="de.1")},now,reader)
        self.assertEqual(verified_rows(dup,now),[])
        report["groups"][0]["sources"]=["https://example.org","https://example.net"]
        self.assertEqual(verified_rows(report,now),[])
        self.assertEqual(verified_rows(build_report(archive,now,lambda url:b"bad"),now),[])
if __name__=="__main__": unittest.main()
