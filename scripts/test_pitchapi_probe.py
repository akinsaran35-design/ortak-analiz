import unittest,io
from email.message import Message
from urllib.error import HTTPError
from pitchapi_probe import run,catalog,TARGETS

class ProbeTests(unittest.TestCase):
    def test_missing_key_no_request(self):
        def fail(*args):
            self.fail("must not request without key")
        self.assertEqual(run("",fail)["status"],"missing_key")
    def test_unique_exact_country_and_name(self):
        rows=[dict(name=name,country=country,id="l_"+str(i).zfill(6)) for i,(_,country,name) in enumerate(TARGETS)]
        r=run("mock",lambda path,key:dict(leagues=rows))
        self.assertEqual(r["matched"],6)
        self.assertFalse(r["xgValidated"])
        self.assertFalse(r["xtValidated"])
        self.assertEqual(catalog(rows+[dict(rows[0])])[0]["status"],"missing_or_ambiguous")
    def test_safe_forbidden_diagnostics(self):
        def failing(content_type,body):
            def reader(*args):
                h=Message()
                h["Content-Type"]=content_type
                raise HTTPError("https://api.pitchapi.dev/v1/leagues",403,"forbidden",h,io.BytesIO(body))
            return run("mock",reader)
        r=failing("application/json",b'{"error":{"code":"FORBIDDEN","message":"sensitive"}}')
        self.assertEqual(r["httpStatus"],403)
        self.assertEqual(r["providerErrorCode"],"FORBIDDEN")
        self.assertNotIn("sensitive",str(r))
        r=failing("text/html",b"<html>secret</html>")
        self.assertEqual(r["responseFormat"],"html")
        self.assertNotIn("secret",str(r))
        r=failing("application/json",b'{"error":{"code":"unknown-secret"}}')
        self.assertIsNone(r["providerErrorCode"])
    def test_invalid_payload(self):
        self.assertEqual(run("mock",lambda *args:None)["status"],"connection_or_schema_error")
if __name__=="__main__":
    unittest.main()
