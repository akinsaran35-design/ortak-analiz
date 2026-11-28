import unittest
from datetime import datetime
from api_football_referee_probe import probe,inspect
NOW=datetime.fromisoformat("2026-11-28T14:00:00+03:00")
def response(day):
    return dict(errors=[],results=1,paging=dict(current=1,total=1),response=[
        dict(fixture=dict(id=1,date=day+"T12:00:00+03:00",status=dict(short="FT"),referee="Example"),league=dict(id=78))])
class ProbeTests(unittest.TestCase):
    def test_guard(self):
        def reader(key,path):
            self.assertEqual(path,"status")
            return dict(errors=[],response=dict(requests=dict(current=79,limit_day=100),subscription=dict(active=True,plan="Free")))
        self.assertEqual(probe("test",NOW,reader)["requestsAttempted"],0)
    def test_bounded(self):
        paths=[]
        def reader(key,path):
            paths.append(path)
            if path=="status":return dict(errors=[],response=dict(requests=dict(current=78,limit_day=100),subscription=dict(active=True,plan="Free")))
            return response(path.split("date=")[1].split("&")[0])
        result=probe("test",NOW,reader)
        self.assertEqual(result["requestsAttempted"],2)
        self.assertEqual(len(paths),3)
        self.assertEqual(result["days"][0]["groups"][0]["withReferee"],1)
        self.assertNotIn("Example",str(result))
    def test_fixture_join_without_extra_paid_requests(self):
        paths=[]
        def reader(key,path):
            paths.append(path)
            if path=="status":return dict(errors=[],response=dict(requests=dict(current=78,limit_day=100),subscription=dict(active=True,plan="Free")))
            day=path.split("date=")[1].split("&")[0]
            doc=response(day)
            row=doc["response"][0]
            row["fixture"].update(status=dict(short="NS"))
            row["league"].update(country="Germany",name="Bundesliga")
            row["teams"]=dict(home=dict(name="Alpha"),away=dict(name="Beta"))
            return doc
        def fixtures(day):
            return [dict(league="de.1",rows=[dict(eventId="321",home="Alpha",away="Beta",kickoff=day+"T12:00:00+03:00",state="pre",status="STATUS_SCHEDULED")])]
        r=probe("test",NOW,reader,fixture_reader=fixtures)
        self.assertEqual(len(paths),3)
        join=r["days"][1]["fixtureJoin"]
        self.assertEqual({k:join[k] for k in ("eligibleIdentities","matched","withReferee","status")},dict(eligibleIdentities=1,matched=1,withReferee=1,status="checked"))
        self.assertEqual(next(x for x in join["diagnostics"] if x["league"]=="de.1")["counts"],dict(eligible=1,matched_with_referee=1))
        self.assertNotIn("Example",str(r))
        def fail(day):raise OSError("unavailable")
        r=probe("test",NOW,reader,fixture_reader=fail)
        self.assertEqual(r["days"][1]["fixtureJoin"]["status"],"unverified")
    def test_incomplete(self):
        doc=response("2026-11-28")
        doc["paging"]["total"]=2
        with self.assertRaises(ValueError):inspect(doc,"2026-11-28")
if __name__=="__main__":unittest.main()
