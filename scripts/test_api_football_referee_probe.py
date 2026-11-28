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
    def test_incomplete(self):
        doc=response("2026-11-28")
        doc["paging"]["total"]=2
        with self.assertRaises(ValueError):inspect(doc,"2026-11-28")
if __name__=="__main__":unittest.main()
