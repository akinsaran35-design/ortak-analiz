import unittest
from datetime import datetime,timezone,timedelta
from api_football_sample_quality import inspect_sample

class SampleQualityTests(unittest.TestCase):
    def test_freshness_duplicates_and_pagination(self):
        now=datetime(2026,11,28,12,tzinfo=timezone.utc)
        def row(i,age,starts=60):
            return {"fixture":{"id":i,"date":(now+timedelta(minutes=starts)).isoformat()},
                    "update":(now-timedelta(minutes=age)).isoformat(),"bookmakers":[{}]}
        doc={"paging":{"current":1,"total":3},"response":[row(1,15),row(2,90),row(3,240),
             row(4,5),row(4,10),row(5,5,-1),row(6,-1),{}]}
        result=inspect_sample(doc,now)
        self.assertEqual(result["uniqueFutureEvents"],3)
        self.assertEqual(result["freshWithin30Minutes"],1)
        self.assertEqual(result["observedWithin3Hours"],2)
        self.assertEqual(result["duplicateOrInvalidRows"],5)
        self.assertFalse(result["sampleComplete"])
        self.assertEqual(result["totalPages"],3)
    def test_missing_pagination_is_not_complete(self):
        now=datetime.now(timezone.utc)
        self.assertFalse(inspect_sample({"response":[]},now)["sampleComplete"])
        self.assertTrue(inspect_sample({"response":[],"paging":{"current":1,"total":0}},now)["sampleComplete"])

if __name__=="__main__":unittest.main()
