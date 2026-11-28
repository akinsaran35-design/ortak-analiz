import unittest,hashlib
from datetime import datetime,timezone
from unittest.mock import patch
from check_frozen_cohort import check
class FrozenCohortTests(unittest.TestCase):
    def test_valid_and_tampered(self):
        model=b"frozen-model"
        meta=dict(version="6.67",weight=.5,modelSha256=hashlib.sha256(model).hexdigest(),featureKeys=[str(i) for i in range(119)])
        ledger=dict(version="6.67",modelSha256=meta["modelSha256"],forecasts={},settlements={},quarantine={})
        now=datetime.now(timezone.utc)
        check(model,meta,ledger,now,"6.67",{})
        with self.assertRaises(ValueError):check(b"tampered",meta,ledger,now,"6.67",{})
        with self.assertRaises(ValueError):check(model,dict(meta,featureKeys=["a"]*119),ledger,now,"6.67",{})
        with self.assertRaises(ValueError):check(model,meta,dict(ledger,modelSha256="wrong"),now,"6.67",{})
if __name__=="__main__":unittest.main()
