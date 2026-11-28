import unittest
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
    def test_invalid_payload(self):
        self.assertEqual(run("mock",lambda *args:None)["status"],"connection_or_schema_error")
if __name__=="__main__":
    unittest.main()
