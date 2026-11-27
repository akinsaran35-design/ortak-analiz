import unittest
from tff_referee_source_probe import extract,SAMPLES
class Tests(unittest.TestCase):
    def raw(self,roles,day="22.11.2026"):
        return ("<p>Süper Lig "+day+"</p><a>KASIMPAŞA A.Ş.</a><a>CORENDON ALANYASPOR</a>"+roles).encode()
    def test_referee_only(self):
        r=extract(self.raw("<a>Ref A(Hakem)</a><a>Ref B(1. Yardımcı Hakem)</a><a>Ref C(VAR)</a>"),SAMPLES[0])
        self.assertEqual(r,dict(status="observed",refereeLabel="Ref A"))
    def test_legacy_turkish(self):
        html='<meta charset="windows-1254"><p>Süper Lig 22.11.2026</p><a>KASIMPAŞA A.Ş.</a><a>CORENDON ALANYASPOR</a><a>DAVUT DAKUL ÇELİK(Hakem)</a>'
        self.assertEqual(extract(html.encode("cp1254"),SAMPLES[0])["refereeLabel"],"DAVUT DAKUL ÇELİK")
    def test_ambiguous(self):
        self.assertEqual(extract(self.raw("<a>A(Hakem)</a><a>B(Hakem)</a>"),SAMPLES[0])["status"],"ambiguous")
    def test_missing(self):
        self.assertEqual(extract(self.raw("<a>A(VAR)</a>"),SAMPLES[0])["status"],"missing")
    def test_wrong_date(self):
        with self.assertRaises(ValueError):extract(self.raw("<a>A(Hakem)</a>","21.11.2026"),SAMPLES[0])
if __name__=="__main__":unittest.main()
