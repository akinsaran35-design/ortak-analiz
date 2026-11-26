import importlib
import sys
import unittest
from unittest.mock import patch
from datetime import date,timedelta
from pathlib import Path

class BacktestImportTests(unittest.TestCase):
    def test_import_has_no_side_effects(self):
        sys.modules.pop("backtest",None)
        with patch("urllib.request.urlopen",side_effect=AssertionError("network on import")) as network, patch.object(Path,"write_text",side_effect=AssertionError("write on import")) as writer:
            mod=importlib.import_module("backtest")
            network.assert_not_called()
            writer.assert_not_called()
        history=[(date(2026,1,1)+timedelta(days=i),"A","B",2,1) for i in range(10)]
        self.assertEqual(len(mod.predict(history,"A","B")),3)
        self.assertEqual(len(mod.weighted_predict(history,"A","B")),3)
        self.assertTrue(callable(mod.main))
    def test_explicit_execution(self):
        import backtest
        with patch.object(backtest,"LEAGUES",["en.1"]),patch.object(backtest,"fetch",return_value=[]) as fetch,patch.object(Path,"write_text") as write:
            backtest.main()
            self.assertEqual(fetch.call_count,len(backtest.seasons))
            self.assertEqual(write.call_count,2)
            import json
            report=json.loads(write.call_args.args[0])
            self.assertEqual(report["version"],"2.1")
            self.assertFalse(report["modelCalibrated"])
            self.assertIn("modelSelectionV42",report)
if __name__=="__main__": unittest.main()
