import unittest
from datetime import datetime,timedelta
from automatic_results import verified_rows,TR
from verified_results import settle_verified

class AutoResultsTests(unittest.TestCase):
    def test_fresh_and_exact(self):
        now=datetime(2026,11,26,17,tzinfo=TR)
        sources=["https://football-data.co.uk/mmz4281/2627/E1.csv","https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2/scoreboard?dates=20261125"]
        row={"date":"2026-11-25","home":"A","away":"B","csv":[2,1],"espn":[2,1],"status":"corroborated"}
        report={"updatedAt":now.isoformat(),"errors":[],"sources":sources,"rows":[row]}
        rows=verified_rows(report,now)
        self.assertEqual(len(rows),1)
        record={"date":"2026-11-25","league":"en.2","home":"A","away":"B","recordedAt":"2026-11-24T18:00:00+03:00","result":None,"candidate":.6}
        self.assertEqual(settle_verified({"x":record},rows,now),1)
        self.assertEqual(record["candidate"],.6)
        self.assertEqual(record["resultSources"],sources)
        self.assertEqual(verified_rows(report,now+timedelta(minutes=31)),[])
        self.assertEqual(verified_rows(dict(report,errors=["offline"]),now),[])
        self.assertEqual(verified_rows(dict(report,sources=sources[:1]),now),[])
        self.assertEqual(verified_rows(dict(report,rows=[dict(row,espn=[0,0])]),now),[])
        self.assertEqual(verified_rows(dict(report,rows=[dict(row,status="archive_conflict")]),now),[])

if __name__=="__main__": unittest.main()
