import unittest
from api_football_access_probe import probe

def status(used=0, limit=100, plan="Free", active=True):
    return {"errors":[],"response":{"subscription":{"plan":plan,"active":active},
        "requests":{"current":used,"limit_day":limit}}}

class AccessTests(unittest.TestCase):
    def test_missing_secret(self):
        def fail(*args): self.fail("Unexpected request")
        self.assertEqual(probe("",fail)["status"],"missing_secret")
    def test_quota_and_plan_guards(self):
        for doc in (status(used=90),status(plan="Pro"),status(active=False)):
            calls=[]
            def read(key,path):
                calls.append(path)
                return doc
            out=probe("test",read)
            self.assertEqual(calls,["status"])
            self.assertEqual(out["oddsRequestsAttempted"],0)
    def test_valid_and_empty(self):
        for rows in ([{"private":"not printed"}],[]):
            calls=[]
            def read(key,path):
                calls.append(path)
                return status() if path=="status" else {"errors":[],"response":rows}
            out=probe("test",read)
            self.assertEqual(len(calls),2)
            self.assertEqual(out["sampleEventCount"],len(rows))
            self.assertNotIn("private",str(out))
    def test_api_errors(self):
        def read(key,path):
            return status() if path=="status" else {"errors":{"plan":"private detail"}}
        out=probe("test",read)
        self.assertEqual(out["oddsAccess"],"api_error")
        self.assertNotIn("private detail",str(out))

if __name__=="__main__": unittest.main()
