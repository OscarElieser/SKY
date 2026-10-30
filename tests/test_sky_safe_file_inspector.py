"""Inspección real limitada sin acceso al sistema de archivos externo."""
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from neural_core import sky_safe_file_inspector as inspector
from neural_core import sky_safe_workspace as ws

class InspectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"SKY_SAFE_WORKSPACE_ROOT":str(Path(self.tmp.name)/"safe")})
        self.env.start()
    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()
    def test_text(self):
        p=ws._root()/"real.md";p.write_text("SKY aprende a leer",encoding="utf-8")
        out=inspector.inspect("real.md")
        self.assertIn("SKY aprende",out["text"])
        self.assertTrue(out["read_only"])
        self.assertFalse(out["external_services_called"])
    def test_docx(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w") as z:
            z.writestr("word/document.xml",'<w:document xmlns:w="http://w"><w:t>Documento real</w:t></w:document>')
        (ws._root()/"demo.docx").write_bytes(buf.getvalue())
        self.assertIn("Documento real",inspector.inspect("demo.docx")["text"])
    def test_traversal_and_bad_xml(self):
        with self.assertRaises(ws.WorkspaceError):inspector.inspect("../clave.txt")
        bad=io.BytesIO()
        with zipfile.ZipFile(bad,"w") as z:
            z.writestr("word/document.xml","<!DOCTYPE x><x/>")
        (ws._root()/"mal.docx").write_bytes(bad.getvalue())
        with self.assertRaises(ws.WorkspaceError):inspector.inspect("mal.docx")


    def test_utf8_multibyte_limit_is_not_a_false_decode_error(self):
        # Una tilde puede caer justo en el borde de la vista limitada.
        p=ws._root()/"utf8.md"
        p.write_bytes(b"x"*14999 + "ñ".encode("utf-8") + b"hola")
        result=inspector.inspect("utf8.md")
        self.assertTrue(result["read_only"])
        self.assertEqual(len(result["text"]),15000)
        self.assertTrue(result["text"].endswith("ñ"))

    def test_non_utf8_text_is_not_silently_accepted(self):
        p=ws._root()/"invalid.md"
        p.write_bytes(b"abc\xff")
        with self.assertRaises(ws.WorkspaceError):
            inspector.inspect("invalid.md")

if __name__=="__main__":unittest.main()
