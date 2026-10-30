"""Validación JSON ejecutable, sin filtrar fuentes a memoria."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from neural_core import sky_verified_roles as roles

class JSONTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict("os.environ",{"SKY_ROLE_LESSONS_DB":str(Path(self.tmp.name)/"a.db"),
                   "SKY_VERIFIED_ROLES_DB":str(Path(self.tmp.name)/"b.db")})
        self.env.start()
    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()
    def test_success_types(self):
        for src,kind in (('{"a":true}',"object"),("[1,2]","array"),("null","null")):
            with self.subTest(src=src):
                x=roles.run_plan([{"id":"j","role":"programacion","tool":"validar_json","args":{"source":src}}])
                self.assertEqual(x["status"],"VERIFIED_LIMITED_SCOPE")
                self.assertEqual(x["steps"][0]["result"]["top_level"],kind)
                self.assertFalse(x["steps"][0]["result"]["code_executed"])
    def test_invalid_json_and_duplicates(self):
        for src in ('{"x":1,"x":2}','{"nested":{"x":2,"x":5}}','{"x":NaN}','{"x":}'):
            with self.subTest(src=src):
                x=roles.run_plan([{"id":"j","role":"programacion","tool":"validar_json","args":{"source":src}}])
                self.assertEqual(x["status"],"FAILED")
    def test_secret_not_persisted(self):
        private="SECRET_72838484_SSS"
        roles.run_plan([{"id":"j","role":"programacion","tool":"validar_json",
                        "args":{"source":'{"private":"'+private+'"}'}}])
        self.assertNotIn(private.encode(),(Path(self.tmp.name)/"a.db").read_bytes())
        self.assertNotIn(private.encode(),(Path(self.tmp.name)/"b.db").read_bytes())
    def test_tool_is_registered(self):
        self.assertIn("validar_json",roles.TOOLS["programacion"])

if __name__=="__main__":
    unittest.main()
