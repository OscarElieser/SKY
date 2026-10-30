"""Integración HTTP real de SKY Safe Files, con aprobaciones y trabajo aislado.

TestClient usa una autenticación de prueba que NO sustituye pruebas MFA del
servidor real. No usa directorios del propietario ni hardware Android/Windows.
"""
from __future__ import annotations
from io import BytesIO
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.testclient import TestClient


class SafeFilesHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake=types.ModuleType("metaverse.api")
        def require_key(x_sky_key: str=Header(default="")):
            if x_sky_key != "owner-safe-files-test-2026":
                raise HTTPException(401,"Invalid test key")
        fake.require_key=require_key
        cls.fake_api=patch.dict(sys.modules,{"metaverse.api":fake})
        cls.fake_api.start()
        from metaverse import sky_safe_files_api
        cls.endpoint=sky_safe_files_api
        app=FastAPI()
        app.include_router(sky_safe_files_api.router)
        cls.client=TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.fake_api.stop()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"SKY_SAFE_WORKSPACE_ROOT":str(Path(self.tmp.name)/"space")})
        self.env.start()
        self.h={"X-SKY-KEY":"owner-safe-files-test-2026"}
        self.pin=patch.object(self.endpoint,"exigir_pin",side_effect=self._pin)
        self.pin.start()

    def tearDown(self):
        self.pin.stop()
        self.env.stop()
        self.tmp.cleanup()

    @staticmethod
    def _pin(request,reason):
        if request.headers.get("X-SKY-PIN")!="123456":
            raise HTTPException(403,"PIN needed")

    def prepare(self,spec,headers=None):
        return self.client.post("/api/sky/safe-files/prepare",headers=headers or self.h,json={"spec":spec})

    def commit(self,spec,prepared,headers=None):
        result=prepared.json()
        preview=result["preview"]
        return self.client.post("/api/sky/safe-files/commit",headers=headers or self.h,json={
            "spec":spec,"approval_token":result["approval_token"],
            "expected_sha":preview["expected_sha"],
            "destination_state":preview["destination_state"]})

    def add(self,name="informe.md",text="Primera versión"):
        spec={"op":"create","name":name,"text":text}
        first=self.prepare(spec)
        self.assertEqual(first.status_code,200,first.text)
        second=self.commit(spec,first)
        self.assertEqual(second.status_code,200,second.text)
        return second

    def test_auth_and_explicit_approval_no_implicit_creation(self):
        self.assertEqual(self.client.get("/api/sky/safe-files/list").status_code,401)
        spec={"op":"create","name":"nuevo.md","text":"Contenido de prueba"}
        p=self.prepare(spec)
        self.assertEqual(p.status_code,200,p.text)
        folder=Path(os.environ["SKY_SAFE_WORKSPACE_ROOT"])
        self.assertFalse((folder/"nuevo.md").exists())
        no=self.client.post("/api/sky/safe-files/commit",headers=self.h,json={
            "spec":spec,"approval_token":"a"*40,"expected_sha":"absent"})
        self.assertEqual(no.status_code,409)
        done=self.commit(spec,p)
        self.assertEqual(done.status_code,200,done.text)
        self.assertTrue(done.json()["verified_after_write"])
        self.assertEqual((folder/"nuevo.md").read_text(),"Contenido de prueba")
        self.assertEqual(self.commit(spec,p).status_code,409)
        listing=self.client.get("/api/sky/safe-files/list",headers=self.h).json()["files"]
        self.assertEqual(listing[0]["name"],"nuevo.md")
        dl=self.client.get("/api/sky/safe-files/download/nuevo.md",headers=self.h)
        self.assertEqual(dl.content,b"Contenido de prueba")
        self.assertIn("attachment",dl.headers["content-disposition"])

    def test_approval_binds_to_full_parameters_and_session(self):
        spec={"op":"create","name":"safe.txt","text":"Versión correcta"}
        p=self.prepare(spec)
        altered=dict(spec,text="Versión alterada")
        self.assertEqual(self.commit(altered,p).status_code,409)
        alternate={"X-SKY-KEY":self.h["X-SKY-KEY"],"X-SKY-SESSION":"other-session"}
        self.assertEqual(self.commit(spec,p,alternate).status_code,409)
        self.assertEqual(self.commit(spec,p).status_code,200)

    def test_stale_preview_rejects_replace(self):
        self.add("original.txt","Inicial")
        spec={"op":"replace","name":"original.txt","text":"Otra versión"}
        p=self.prepare(spec)
        folder=Path(os.environ["SKY_SAFE_WORKSPACE_ROOT"])
        (folder/"original.txt").write_text("Cambio concurrente")
        ret=self.commit(spec,p,{**self.h,"X-SKY-PIN":"123456"})
        self.assertEqual(ret.status_code,409)
        self.assertEqual((folder/"original.txt").read_text(),"Cambio concurrente")

    def test_append_rename_recoverable_trash_and_restore(self):
        self.add("clase.txt","Tema")
        folder=Path(os.environ["SKY_SAFE_WORKSPACE_ROOT"])
        for spec in (
            {"op":"append","name":"clase.txt","text":" final"},
            {"op":"rename","name":"clase.txt","new_name":"clase-final.txt"},
        ):
            p=self.prepare(spec)
            self.assertEqual(self.commit(spec,p).status_code,403)
            approved=self.commit(spec,p,{**self.h,"X-SKY-PIN":"123456"})
            self.assertEqual(approved.status_code,200,approved.text)
        self.assertEqual((folder/"clase-final.txt").read_text(),"Tema final")
        trash={"op":"trash","name":"clase-final.txt"}
        p=self.prepare(trash)
        r=self.commit(trash,p,{**self.h,"X-SKY-PIN":"123456"})
        self.assertEqual(r.status_code,200,r.text)
        ident=r.json()["result"]["trash_id"]
        self.assertFalse((folder/"clase-final.txt").exists())
        restore={"op":"restore","name":"clase-final.txt","trash_id":ident}
        p2=self.prepare(restore)
        end=self.commit(restore,p2,{**self.h,"X-SKY-PIN":"123456"})
        self.assertEqual(end.status_code,200,end.text)
        self.assertEqual((folder/"clase-final.txt").read_text(),"Tema final")
        self.assertEqual(self.prepare(restore).status_code,409)

    def test_escape_and_symlink_are_rejected(self):
        for name in ("../outside.txt","/tmp/outside.txt","my/folder.txt",".env","archivo.exe",
                     "CON.txt","NUL.md","LPT1.pdf","AUX.xlsx"):
            with self.subTest(name=name):
                self.assertEqual(self.prepare({"op":"create","name":name,"text":"data"}).status_code,422)
        folder=Path(os.environ["SKY_SAFE_WORKSPACE_ROOT"])
        folder.mkdir(parents=True,exist_ok=True)
        original=Path(self.tmp.name)/"external.txt"
        original.write_text("Do not touch me")
        link=folder/"linked.txt"
        try:link.symlink_to(original)
        except (NotImplementedError,OSError):self.skipTest("No symlink support on runner")
        self.assertEqual(self.prepare({"op":"replace","name":"linked.txt","text":"ATTACK"}).status_code,422)
        self.assertEqual(original.read_text(),"Do not touch me")

    def test_docx_and_xlsx_are_real_files(self):
        samples=[
            {"name":"reporte.docx","document":{"kind":"docx","title":"Informe SKY",
                "content":"# Objetivos\nAprender con evidencia"}},
            {"name":"notas.xlsx","document":{"kind":"xlsx","title":"Notas SKY",
                "content":"Resultados","headers":["Estudiante","Nota"],
                "rows":[["A",80],["B",95]]}},
            {"name":"diapositivas.pptx","document":{"kind":"pptx","title":"Clases SKY",
                "content":"# Objetivos\nFormación profesional"}},
            {"name":"informe.pdf","document":{"kind":"pdf","title":"SKY",
                "content":"# Informe\nResultados locales"}},
        ]
        for item in samples:
            with self.subTest(name=item["name"]):
                spec={"op":"create",**item}
                p=self.prepare(spec)
                self.assertEqual(p.status_code,200,p.text)
                r=self.commit(spec,p)
                self.assertEqual(r.status_code,200,r.text)
                data=self.client.get("/api/sky/safe-files/download/"+item["name"],headers=self.h).content
                if item["name"].endswith(".pdf"):
                    self.assertTrue(data.startswith(b"%PDF-"))
                else:
                    self.assertTrue(zipfile.is_zipfile(BytesIO(data)))
                self.assertEqual(r.json()["result"]["bytes"],len(data))
                self.assertTrue(r.json()["verified_after_write"])

    def test_audit_is_content_free(self):
        private="very-secret-text-999999"
        self.add("privado.md",private)
        audits=self.client.get("/api/sky/safe-files/audit",headers=self.h)
        self.assertEqual(audits.status_code,200)
        content=audits.text
        self.assertNotIn(private,content)
        self.assertNotIn("privado.md",content)
        self.assertFalse(audits.json()["contains_file_content"])

    def test_mobile_chat_token_cannot_write(self):
        res=self.client.post("/api/sky/safe-files/prepare",headers={"X-SKY-CHAT-TOKEN":"a"*50},
                             json={"spec":{"op":"create","name":"x.txt","text":"secret"}})
        self.assertEqual(res.status_code,401)

    def test_json_invalid_and_duplicate_keys_rejected_before_approval(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x": }'):
            with self.subTest(text=text):
                p=self.prepare({"op":"create","name":"wrong.json","text":text})
                self.assertEqual(p.status_code,422,p.text)

    def test_confirmations_reject_extra_fields(self):
        p=self.prepare({"op":"create","name":"safe.txt","text":"Hello","private_data":"ignored"})
        self.assertEqual(p.status_code,422)
        p2=self.prepare({"op":"trash","name":"missing.txt","text":"unexpected"})
        self.assertEqual(p2.status_code,422)

    def test_confirmation_prevents_overwriting_existing(self):
        self.add("existing.txt","Original")
        p=self.prepare({"op":"create","name":"existing.txt","text":"Overwrite"})
        self.assertEqual(p.status_code,409)
        self.assertEqual((Path(os.environ["SKY_SAFE_WORKSPACE_ROOT"])/"existing.txt").read_text(),"Original")

    def test_readonly_text_preview_for_editing(self):
        self.add("lesson.txt","Texto editable")
        response=self.client.get("/api/sky/safe-files/text/lesson.txt",headers=self.h)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["text"],"Texto editable")
        self.assertTrue(response.json()["read_only_preview"])
        self.assertFalse(response.json()["executed"])
        self.assertEqual(self.client.get("/api/sky/safe-files/text/lesson.txt").status_code,401)

    def test_chat_approval_requires_explicit_user_action(self):
        hud=Path("metaverse/static/hud.js").read_text(encoding="utf-8")
        self.assertIn("presentarPropuestaArchivo",hud)
        self.assertIn("data.tipo === 'safe_file_proposal'",hud)
        self.assertIn("confirmar(card,names[spec.op]+' '+spec.name,execute,true)",hud)
        self.assertIn("approval_token:prepared.approval_token",hud)

    def test_hud_has_visible_approval_workflow(self):
        hud=Path("metaverse/static/hud.js").read_text(encoding="utf-8")
        html=Path("metaverse/static/hud.html").read_text(encoding="utf-8")
        api=Path("metaverse/api.py").read_text(encoding="utf-8")
        self.assertIn("abrirArchivosSeguros",hud)
        self.assertIn("btn-safe-files",html)
        self.assertIn("sky_safe_files_router",api)
        self.assertIn("/api/sky/safe-files/prepare",hud)
        self.assertIn("/api/sky/safe-files/commit",hud)


    def test_analysis_preview_prepare_and_commit_require_pin(self):
        self.add("programa.md","SKY aprende con evidencia.\n")
        folder=Path(os.environ["SKY_SAFE_WORKSPACE_ROOT"])
        current=folder/"programa.md"
        url="/api/sky/safe-files/analyze/programa.md"
        self.assertEqual(self.client.get(url).status_code,401)
        analysis=self.client.get(url,headers=self.h)
        self.assertEqual(analysis.status_code,200,analysis.text)
        report=analysis.json()
        self.assertTrue(report["editable_via_proposal"])
        self.assertFalse(report["file_changed"])
        command={"name":"programa.md","mode":"replace_once",
                 "expected_sha":report["sha256"],"find":"aprende","replacement":"enseña"}
        preview=self.client.post("/api/sky/safe-files/edit/preview",headers=self.h,json=command)
        self.assertEqual(preview.status_code,200,preview.text)
        self.assertIn("enseña",preview.json()["diff"])
        self.assertFalse(preview.json()["committed"])
        self.assertEqual(current.read_text(encoding="utf-8"),"SKY aprende con evidencia.\n")
        prepare=self.client.post("/api/sky/safe-files/edit/prepare",headers=self.h,
                                 json={**command,"proposal_digest":preview.json()["proposal_digest"]})
        self.assertEqual(prepare.status_code,200,prepare.text)
        spec=prepare.json()["spec"]
        self.assertEqual(spec["text"],"SKY enseña con evidencia.\n")
        self.assertEqual(self.commit(spec,prepare).status_code,403)
        self.assertEqual(current.read_text(encoding="utf-8"),"SKY aprende con evidencia.\n")
        completed=self.commit(spec,prepare,{**self.h,"X-SKY-PIN":"123456"})
        self.assertEqual(completed.status_code,200,completed.text)
        self.assertTrue(completed.json()["verified_after_write"])
        self.assertEqual(current.read_text(encoding="utf-8"),"SKY enseña con evidencia.\n")
        self.assertEqual(self.commit(spec,prepare,{**self.h,"X-SKY-PIN":"123456"}).status_code,409)

    def test_changed_file_between_preview_and_prepare_is_rejected(self):
        self.add("informe.txt","Versión inicial")
        target=Path(os.environ["SKY_SAFE_WORKSPACE_ROOT"])/"informe.txt"
        sha=self.client.get("/api/sky/safe-files/analyze/informe.txt",headers=self.h).json()["sha256"]
        cmd={"name":"informe.txt","mode":"replace_once",
             "expected_sha":sha,"find":"inicial","replacement":"actualizada"}
        preview=self.client.post("/api/sky/safe-files/edit/preview",headers=self.h,json=cmd)
        self.assertEqual(preview.status_code,200,preview.text)
        target.write_text("Otra actualización externa",encoding="utf-8")
        response=self.client.post("/api/sky/safe-files/edit/prepare",headers=self.h,
                   json={**cmd,"proposal_digest":preview.json()["proposal_digest"]})
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(target.read_text(),"Otra actualización externa")

    def test_change_of_requested_text_needs_a_new_preview(self):
        self.add("clase.md","Aprendizaje digital")
        sha=self.client.get("/api/sky/safe-files/analyze/clase.md",headers=self.h).json()["sha256"]
        cmd={"name":"clase.md","mode":"replace_once",
             "expected_sha":sha,"find":"digital","replacement":"seguro"}
        preview=self.client.post("/api/sky/safe-files/edit/preview",headers=self.h,json=cmd)
        denied=self.client.post("/api/sky/safe-files/edit/prepare",headers=self.h,
                   json={**cmd,"replacement":"inseguro",
                         "proposal_digest":preview.json()["proposal_digest"]})
        self.assertEqual(denied.status_code,409,denied.text)
        self.assertEqual((Path(os.environ["SKY_SAFE_WORKSPACE_ROOT"])/"clase.md").read_text(),
                         "Aprendizaje digital")

    def test_docx_is_readonly_and_json_validation_still_applies(self):
        self.add("data.json",'{"enabled":true}')
        sha=self.client.get("/api/sky/safe-files/analyze/data.json",headers=self.h).json()["sha256"]
        bad={"name":"data.json","mode":"replace_once","expected_sha":sha,
             "find":"true","replacement":"NaN"}
        denied=self.client.post("/api/sky/safe-files/edit/preview",headers=self.h,json=bad)
        self.assertEqual(denied.status_code,422,denied.text)
        self.assertEqual(self.client.get("/api/sky/safe-files/text/data.json",
                                         headers=self.h).json()["text"],'{"enabled":true}')
        doc={"op":"create","name":"clase.docx",
             "document":{"kind":"docx","title":"Clase","content":"# Contenido\nSKY IA"}}
        prepared=self.prepare(doc)
        self.assertEqual(prepared.status_code,200,prepared.text)
        self.assertEqual(self.commit(doc,prepared).status_code,200)
        analysis=self.client.get("/api/sky/safe-files/analyze/clase.docx",headers=self.h)
        self.assertEqual(analysis.status_code,200,analysis.text)
        self.assertFalse(analysis.json()["editable_via_proposal"])
        denied=self.client.post("/api/sky/safe-files/edit/preview",headers=self.h,json={
            "name":"clase.docx","mode":"replace_once",
            "expected_sha":analysis.json()["sha256"],"find":"SKY","replacement":"IA"})
        self.assertEqual(denied.status_code,422,denied.text)

    def test_hud_has_real_three_stage_edit_flow(self):
        hud=Path("metaverse/static/hud.js").read_text(encoding="utf-8")
        self.assertIn("abrirAnalisisSeguro",hud)
        self.assertIn("/api/sky/safe-files/edit/preview",hud)
        self.assertIn("/api/sky/safe-files/edit/prepare",hud)
        self.assertIn("/api/sky/safe-files/commit",hud)
        self.assertIn("Analizar y proponer",hud)

if __name__=="__main__":
    unittest.main()
