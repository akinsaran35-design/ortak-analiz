import unittest,json,copy
from datetime import datetime
from results_source_pilot import TR
from main_leagues_ml_settlement import CODES,ESPN,VERSION,identity
from extra_ml_settlement import settle,summarize
from extra_league_prospective import key
class MainSettlementTests(unittest.TestCase):
    def test_double_source_and_immutable(self):
        m=dict(over15=.8,over25=.6,btts=.5)
        f=dict(league="en.1",date="2026-11-29",home=identity("en.1","Manchester United"),away=identity("en.1","Liverpool"),eventId="123",kickoff="2026-11-29T12:00:00+00:00",recordedAt="2026-11-28T12:00:00+03:00",historyThrough="2026-11-27",policyVersion=VERSION,modelSha256="x",poisson=m,catboost=m,candidate=m)
        k=key(f)
        ledger=dict(version=VERSION,modelSha256="x",forecasts={k:f},settlements={},quarantine={})
        meta=dict(version=VERSION,modelSha256="x",frozenAt="2026-11-28T11:00:00+03:00")
        now=datetime(2026,12,1,12,tzinfo=TR)
        event=dict(id="123",date="2026-11-29T12:00:00Z",competitions=[dict(date="2026-11-29T12:00:00Z",status=dict(type=dict(name="STATUS_FULL_TIME",completed=True)),competitors=[dict(homeAway="home",team=dict(displayName="Manchester United"),score="2"),dict(homeAway="away",team=dict(displayName="Liverpool"),score="1")])])
        def reader(url):
            if "football-data" in url:
                self.assertTrue(url.endswith("/E0.csv"))
                return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n29/11/2026,Man United,Liverpool,2,1\n"
            self.assertIn("/eng.1/scoreboard",url)
            return json.dumps(dict(events=[event])).encode()
        original=copy.deepcopy(ledger["forecasts"])
        kwargs=dict(reader=reader,version=VERSION,codes=CODES,identity_fn=identity,espn_codes=ESPN)
        self.assertEqual(settle(ledger,meta,now,**kwargs)[0],1)
        self.assertEqual(settle(ledger,meta,now,**kwargs)[0],0)
        self.assertEqual(ledger["forecasts"],original)
        self.assertEqual(summarize(ledger,version=VERSION)["validSettled"],1)
        event["competitions"][0]["competitors"][0]["score"]="3"
        settle(ledger,meta,now,**kwargs)
        self.assertEqual(summarize(ledger,version=VERSION)["validSettled"],0)
        self.assertEqual(summarize(ledger,version=VERSION)["quarantined"],1)
if __name__=="__main__":unittest.main()
