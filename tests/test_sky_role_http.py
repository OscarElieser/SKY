"""Pruebas HTTP reales con FastAPI TestClient y dependencias aisladas.

La autenticación del propietario se sustituye SOLO aquí por una dependencia
de prueba: NO se afirma haber validado la configuración MFA de producción.
La firma criptográfica, permisos y rate limit móviles tienen suites propias.
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

class ToolHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake = types.ModuleType("metaverse.api")
        def require_key(x_sky_key: str = Header(default="")):
            if x_sky_key != "integration-test-only-key":
                raise HTTPException(status_code=401, detail="Credenciales de prueba inválidas")
            return True
        fake.require_key = require_key
        cls.env_api=patch.dict(sys.modules, {"metaverse.api": fake})
        cls.env_api.start()
        from metaverse import sky_verified_roles_api, sky_home_api, mobile_chat_api
        cls.modules=(sky_verified_roles_api,sky_home_api,mobile_chat_api)
        app=FastAPI()
        app.include_router(sky_verified_roles_api.router)
        app.include_router(sky_home_api.router)
        app.include_router(mobile_chat_api.router)
        cls.client=TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.env_api.stop()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{
            "SKY_ROLE_LESSONS_DB":str(Path(self.temp.name)/"lessons.db"),
            "SKY_VERIFIED_ROLES_DB":str(Path(self.temp.name)/"metrics.db"),
            "SKY_MOBILE_AGENT_DB":str(Path(self.temp.name)/"mobile-agent.db"),
            "SKY_MOBILE_CHAT_DB":str(Path(self.temp.name)/"mobile-chat.db"),
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_dashboard_and_dispatch_auth(self):
        url="/api/sky/verified-roles/dashboard"
        self.assertEqual(self.client.get(url).status_code,401)
        headers={"X-SKY-KEY":"integration-test-only-key"}
        self.assertEqual(self.client.get(url,headers=headers).status_code,200)
        result=self.client.post("/api/sky/verified-roles/dispatch",headers=headers,
                                json={"task":"cuánto es 7+5","args":{"expression":"7+5"}})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()["execution"]["steps"][0]["result"]["value"],12)

    def test_home_chat_real_without_model(self):
        url="/api/sky/home/chat"
        body={"texto":"Valida JSON: {\"value\":true}"}
        self.assertEqual(self.client.post(url,json=body).status_code,401)
        result=self.client.post(url,headers={"X-SKY-KEY":"integration-test-only-key"},json=body)
        self.assertEqual(result.status_code,200,result.text)
        result=result.json()
        self.assertIn("sintaxis válida",result["respuesta"])
        self.assertFalse(result["nube"])
        self.assertFalse(result["acciones_ejecutadas"])

    def test_mobile_chat_requires_real_device_session(self):
        from neural_core import sky_mobile_agent as agent
        d=agent.pair(agent.pairing_code()["code"],"Android integrado")
        did, agent_key=d["device_id"],d["token"]
        url="/api/sky/mobile-chat/chat"
        body={"device_id":did,"texto":"¿Cuánto es 5+6?"}
        self.assertEqual(self.client.post(url,json=body).status_code,401)
        self.assertEqual(self.client.post(url,headers={"X-SKY-CHAT-TOKEN":agent_key},
                                          json=body).status_code,401)
        headers={"X-SKY-KEY":"integration-test-only-key"}
        invited=self.client.post("/api/sky/mobile-chat/invite",headers=headers,json={"device_id":did})
        self.assertEqual(invited.status_code,200,invited.text)
        paired=self.client.post("/api/sky/mobile-chat/pair",
                   headers={"X-SKY-MOBILE-TOKEN":agent_key},
                   json={"device_id":did,"code":invited.json()["code"]})
        self.assertEqual(paired.status_code,200,paired.text)
        chat_token=paired.json()["token"]
        good=self.client.post(url,headers={"X-SKY-CHAT-TOKEN":chat_token},json=body)
        self.assertEqual(good.status_code,200,good.text)
        self.assertIn("11",good.json()["respuesta"])
        self.assertFalse(good.json()["acciones_ejecutadas"])
        self.assertFalse(good.json()["nube"])
        revoked=self.client.post("/api/sky/mobile-chat/revoke",
                                 headers=headers,json={"device_id":did})
        self.assertEqual(revoked.status_code,200)
        self.assertEqual(self.client.post(url,headers={"X-SKY-CHAT-TOKEN":chat_token},
                                          json=body).status_code,401)

    def test_invalid_source_never_claims_success(self):
        result=self.client.post("/api/sky/home/chat",
                   headers={"X-SKY-KEY":"integration-test-only-key"},
                   json={"texto":"Valida JSON: {\"x\":1,\"x\":2}"})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()["verificacion"]["status"],"FAILED")
        self.assertFalse(result.json()["acciones_ejecutadas"])

if __name__=="__main__":
    unittest.main()
