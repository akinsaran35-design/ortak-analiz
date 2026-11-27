import unittest
from tff_match_identity_probe import extract,official_id
class Tests(unittest.TestCase):
    def raw(self,refs='<a href="Default.aspx?hakemId=9&amp;pageId=72">REF A(Hakem)</a>',extra=""):
        return ('<a href="Default.aspx?kulupId=1&amp;pageId=28">A</a><a href="Default.aspx?kulupId=2&amp;pageId=28">B</a><p>Trendyol Süper Lig Adnan Süvari Sezonu (Profesyonel Takım)</p><p>Maç Kodu: 1111</p><p>27.11.2026 - 20:00</p>'+refs+extra).encode()
    def test_identity(self):
        r=extract(self.raw())
        self.assertEqual(r["matchCode"],"1111")
        self.assertEqual(r["kickoff"],"2026-11-27T20:00:00+03:00")
        self.assertEqual(r["clubs"],[dict(id="1",label="A"),dict(id="2",label="B")])
        self.assertEqual(r["referee"],dict(id="9",label="REF A"))
    def test_missing_referee(self):
        self.assertEqual(extract(self.raw(""))["refereeStatus"],"missing")
    def test_ambiguous(self):
        with self.assertRaises(ValueError):extract(self.raw(extra='<p>28.11.2026 - 20:00</p>'))
    def test_external_identity(self):
        self.assertIsNone(official_id("https://example.com/Default.aspx?pageId=72&hakemId=9","72","hakemid"))
    def test_ambiguous_referee(self):
        r=extract(self.raw(extra='<a href="Default.aspx?hakemId=10&amp;pageId=72">REF B(Hakem)</a>'))
        self.assertEqual(r["refereeStatus"],"ambiguous")
if __name__=="__main__":unittest.main()
