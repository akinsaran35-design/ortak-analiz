import unittest
from sportmonks_access_probe import probe,inspect
class Tests(unittest.TestCase):
    def test_empty_and_missing(self):
        def fail(*a):self.fail("unexpected request")
        self.assertEqual(probe("",fail)["requestsAttempted"],0)
        self.assertEqual(probe("test",lambda *_:{"data":[]})["requestsAttempted"],1)
    def test_nonempty_and_duplicates(self):
        row={"id":1,"league_id":501,"scores":[{"private":"do not log"}],"xGFixture":[{"value":1.2}]}
        r=probe("test",lambda *_:{"data":[row]})
        self.assertEqual(r["requestsAttempted"],2)
        self.assertEqual(r["base"]["eligible"],1)
        self.assertEqual(r["xg"]["fieldPresentNonempty"],{"xGFixture":1})
        self.assertNotIn("private",str(r))
        self.assertFalse(r["predictionsEnabled"])
        self.assertEqual(inspect({"data":[row,row]},("scores",))["eligible"],0)
    def test_malformed(self):
        self.assertEqual(probe("test",lambda *_:{"message":"error"})["status"],"unverified")
if __name__=="__main__":unittest.main()
