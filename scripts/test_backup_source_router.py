import unittest
from datetime import datetime,timezone,timedelta
from backup_source_router import route

class RoutingTests(unittest.TestCase):
    def test_source_gate(self):
        now=datetime.now(timezone.utc)
        primary=dict(source="The Odds API",updatedAt=now.isoformat())
        fallback=dict(version="6.94",currentOddsAt=primary["updatedAt"],updatedAt=now.isoformat(),
                      mode="fallback",currentOddsUsable=False,reason="quota_guard")
        calls=[]
        def check(key):
            calls.append(key)
            return {"status":"verified","oddsRequestsAttempted":1}
        result=route(primary,fallback,now,"fake-key",check)
        self.assertTrue(result["backupAttempted"])
        self.assertEqual(len(calls),1)
        for changes in ({"mode":"normal","currentOddsUsable":True},
                        {"currentOddsAt":"bad"},{"updatedAt":(now-timedelta(minutes=11)).isoformat()},
                        {"reason":"unexpected"},{"currentOddsUsable":True}):
            result=route(primary,dict(fallback,**changes),now,"fake-key",check)
            self.assertFalse(result["backupAttempted"])
        self.assertFalse(route(primary,fallback,now,"",check)["backupAttempted"])
        self.assertEqual(len(calls),1)

if __name__=="__main__": unittest.main()
