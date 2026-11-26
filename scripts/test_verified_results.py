import copy
import unittest
from datetime import datetime, timezone, timedelta
from verified_results import settle_verified

class VerifiedResultsTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,26,17,tzinfo=timezone(timedelta(hours=3)))
        self.record={"date":"2026-11-25","league":"en.2","home":"A","away":"B","recordedAt":"2026-11-24T18:00:00+03:00","candidate":.7,"result":None}
        self.result={"date":"2026-11-25","league":"en.2","home":"A","away":"B","result":[2,1],"sources":["https://example.org/a","https://example.net/b"]}
    def test_preserve_prediction(self):
        archive={"key":copy.deepcopy(self.record)}
        self.assertEqual(settle_verified(archive,[self.result],self.now),1)
        self.assertEqual(archive["key"]["candidate"],.7)
        self.assertEqual(archive["key"]["recordedAt"],self.record["recordedAt"])
        self.assertEqual(archive["key"]["result"],[2,1])
        self.assertEqual(settle_verified(archive,[self.result],self.now),0)
    def test_reject_conflict_wrong_date_single_source_late(self):
        for rows in ([self.result,dict(self.result,result=[0,0])],[dict(self.result,date="2026-11-24")],[dict(self.result,sources=["https://example.org/a"])],[dict(self.result,result=[True,1])]):
            archive={"key":copy.deepcopy(self.record)}
            self.assertEqual(settle_verified(archive,rows,self.now),0)
            self.assertIsNone(archive["key"]["result"])
        late={"key":dict(self.record,recordedAt="2026-11-25T10:00:00+03:00")}
        self.assertEqual(settle_verified(late,[self.result],self.now),0)
    def test_tracking_schema(self):
        archive={"key":dict(self.record,league="Championship",match="A – B")}
        self.assertEqual(settle_verified(archive,[self.result],self.now,{"Championship":"en.2"}),1)

if __name__=="__main__": unittest.main()
