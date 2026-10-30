"""Pruebas de edición supervisada, original intocable antes de autorizar."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from neural_core import sky_safe_file_edits as edit
from neural_core import sky_safe_workspace as ws

class EditingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.dict(os.environ,{"SKY_SAFE_WORKSPACE_ROOT":str(Path(self.tmp.name)/"space")})
        self.p.start()
    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()
    def make(self,name="clase.md",body="SKY aprende.\n"):
        p=ws._root()/name
        p.write_text(body,encoding="utf-8")
        return p
    def test_analyze_is_readonly(self):
        p=self.make()
        a=edit.analyze(p.name)
        self.assertEqual(a["sha256"],ws._hash(p))
        self.assertTrue(a["editable_via_proposal"])
        self.assertGreater(a["visible_words"],0)
        self.assertFalse(a["semantic_ai_analysis"])
    def test_replace_preview_prepare_no_write(self):
        p=self.make()
        sha=ws._hash(p)
        v=edit.preview(p.name,"replace_once",sha,"aprende","enseña")
        self.assertIn("enseña",v["diff"])
        self.assertFalse(v["committed"])
        prep=edit.prepare(p.name,"replace_once",sha,"aprende","enseña",v["proposal_digest"])
        self.assertEqual(prep["spec"]["text"],"SKY enseña.\n")
        self.assertEqual(p.read_text(encoding="utf-8"),"SKY aprende.\n")
    def test_reject_stale_hash(self):
        p=self.make()
        sha=ws._hash(p)
        v=edit.preview(p.name,"replace_once",sha,"aprende","enseña")
        with self.assertRaises(ws.WorkspaceConflict):
            edit.prepare(p.name,"replace_once",sha,"aprende","olvida",v["proposal_digest"])
        p.write_text("Cambio concurrente")
        with self.assertRaises(ws.WorkspaceConflict):
            edit.prepare(p.name,"replace_once",sha,"aprende","enseña",v["proposal_digest"])
    def test_ambiguous_replacement_fails(self):
        p=self.make(body="SKY SKY SKY")
        with self.assertRaises(ws.WorkspaceError):
            edit.preview(p.name,"replace_once",ws._hash(p),"SKY","IA")
    def test_invalid_json_fails(self):
        p=self.make("datos.json",'{"ok":true}')
        with self.assertRaises(ws.WorkspaceError):
            edit.preview(p.name,"replace_once",ws._hash(p),"true","NaN")
    def test_append_is_real_proposal_not_write(self):
        p=self.make()
        v=edit.preview(p.name,"append_text",ws._hash(p),"","\nNuevo párrafo.")
        self.assertGreater(v["after_chars"],v["before_chars"])
        self.assertEqual(p.read_text(encoding="utf-8"),"SKY aprende.\n")
    def test_binary_document_cannot_be_changed(self):
        p=ws._root()/"reporte.docx"
        p.write_bytes(b"not a text")
        with self.assertRaises(ws.WorkspaceError):
            edit.preview(p.name,"replace_once",ws._hash(p),"a","b")
    def test_traversal_fails(self):
        with self.assertRaises(ws.WorkspaceError):
            edit.analyze("../private.txt")
    def test_sensitive_content_never_logged(self):
        secret="SENSITIVE_STUDENT_777"
        p=self.make(body="SKY "+secret)
        v=edit.preview(p.name,"replace_once",ws._hash(p),"SKY","Centro")
        edit.prepare(p.name,"replace_once",ws._hash(p),"SKY","Centro",v["proposal_digest"])
        self.assertIn(secret,p.read_text(encoding="utf-8"))
if __name__=="__main__":
    unittest.main()
