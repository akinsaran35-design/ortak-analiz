import unittest
from extra_league_training_inventory import parse_season,deduplicate,build

HEADER="Date,HomeTeam,AwayTeam,FTHG,FTAG\n"

class HistoryTests(unittest.TestCase):
    def test_window_and_schema(self):
        raw=(HEADER+"01/07/2023,A,B,2,1\n30/06/2023,A,B,1,0\n01/08/2024,A,B,0,0\n02/07/2023,C,D,,\n").encode()
        rows,counts=parse_season(raw,"sco.1",2023,"source")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["verification"],"single_source_only")
        self.assertEqual(counts["outsideWindow"],2)
        self.assertEqual(counts["invalidScoreOrIdentity"],1)
        rows,_=parse_season((HEADER+"29/08/2026,A,B,0,0\n30/08/2026,A,B,1,1\n").encode(),"sco.1",2026,"source")
        self.assertEqual(len(rows),1)
        with self.assertRaises(ValueError):
            parse_season(b"wrong,schema\n","sco.1",2023,"source")
    def test_duplicate_and_conflict_exclusion(self):
        r=dict(league="sco.1",date="2023-08-01",home="a",away="b",score=[1,0])
        self.assertEqual(deduplicate([r,r]),([],1,0))
        self.assertEqual(deduplicate([r,dict(r,score=[2,0])]),([],0,1))
    def test_inventory_does_not_claim_verification(self):
        def reader(url):
            if "/2324/" in url:
                return (HEADER+"01/08/2023,A,B,1,0\n").encode()
            raise OSError("mock failure")
        report,rows=build(reader)
        self.assertEqual(report["requestedSources"],24)
        self.assertEqual(report["successfulSources"],6)
        self.assertEqual(report["uniqueTrainingCandidates"],6)
        self.assertEqual(report["independentlyVerified"],0)
        self.assertFalse(report["usedForTraining"])
        self.assertFalse(report["existingArchivesModified"])
if __name__=="__main__":
    unittest.main()
