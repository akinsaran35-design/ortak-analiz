import unittest
from tff_fixture_link_discovery import discover
class Tests(unittest.TestCase):
    def test_links(self):
        html='<a href="Default.aspx?macID=123&amp;pageID=29">Detaylar</a><a href="/Default.aspx?pageID=29&amp;macID=123">same</a><a href="https://www.tff.org/Default.aspx?pageId=29&amp;macId=456">next</a>'
        self.assertEqual([r["matchId"] for r in discover(html.encode())],["123","456"])
    def test_external_and_bad(self):
        html='<a href="https://example.com/Default.aspx?pageID=29&amp;macID=123">x</a><a href="/Default.aspx?pageID=29&amp;macID=123&amp;macID=999">x</a>'
        with self.assertRaises(ValueError):discover(html.encode())
    def test_wrong_page(self):
        with self.assertRaises(ValueError):discover(b'<a href="/Default.aspx?pageID=198&amp;macID=123">x</a>')
if __name__=="__main__":unittest.main()
