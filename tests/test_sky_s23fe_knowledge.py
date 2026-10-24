"""AT&T Samsung S23 FE and owner-approved encrypted document knowledge."""
from __future__ import annotations

import io
import json
import pytest
from fastapi.testclient import TestClient
from cryptography.fernet import Fernet

KEY="sky-s23fe-document-owner-key-for-tests-2026"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_API_KEY",KEY)
    monkeypatch.setenv("SKY_NEURAL_MEMORY_KEY",Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("SKY_KNOWLEDGE_DB",str(tmp_path/"knowledge.sqlite3"))
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED","0")
    from metaverse.api import app
    with TestClient(app) as conn: yield conn


def auth():
    return {"X-SKY-KEY":KEY}


def test_att_s23fe_eligibility_and_tigo_are_not_falsely_verified(client):
    path="/api/sky/mobile-unlock/s23fe/att-tigo"
    assert client.post(path,json={"owner_attested":True}).status_code==401
    assert client.post(path,headers=auth(),json={"owner_attested":False}).status_code==403
    result=client.post(path,headers=auth(),json={
        "owner_attested":True,
        "observed_state":"network_unlock_requested",
        "owner_reports_paid_off":True,
        "att_unlock_confirmation":False,
    })
    assert result.status_code==200,result.text
    item=result.json()
    assert item["device"]=="Samsung Galaxy S23 FE"
    assert item["origin_carrier"]=="AT&T US"
    assert item["target_sim"]=="Tigo Nicaragua"
    assert item["official_unlock_url"]=="https://www.att.com/deviceunlock/"
    assert not item["unlock_performed"]
    assert not item["sky_independently_verified_unlock"]
    assert not item["carrier_unlock_verified"]
    assert not item["owner_reports_tigo_service"]
    assert "60 días" in item["carrier_policy"]
    assert item["checkpoints"][2]["status"]=="pending_official_carrier_decision"


def test_even_owner_success_report_is_not_independent_sky_verification(client):
    r=client.post("/api/sky/mobile-unlock/s23fe/att-tigo",headers=auth(),json={
        "owner_attested":True,
        "att_unlock_confirmation":True,
        "tigo_calls_work":True,"tigo_sms_work":True,"tigo_data_work":True
    })
    assert r.status_code==200,r.text
    body=r.json()
    assert body["owner_reports_tigo_service"]
    assert body["sky_independently_verified_unlock"] is False
    assert body["unlock_performed"] is False
    assert body["checkpoints"][-1]["status"]=="owner_reports_full_service"


def test_document_indexing_requires_express_permission_and_encryption(client,tmp_path):
    from neural_core import sky_knowledge_library as knowledge
    doc=b"# Taller tecnico\nTema: aprendizaje colaborativo\nLa comunidad desarrolla proyectos."
    path="/api/sky/knowledge/documents"
    f=lambda: {"file":("formacion.md",doc,"text/markdown")}
    assert client.post(path,files=f(),data={"owner_attested":"true","consent_to_index":"true"}).status_code==401
    assert client.post(path,headers=auth(),files=f()).status_code==403
    inserted=client.post(path,headers=auth(),files=f(),data={
        "owner_attested":"true","consent_to_index":"true"})
    assert inserted.status_code==201,inserted.text
    value=inserted.json()
    assert value["status"]=="indexed"
    assert value["model_weights_updated"] is False
    assert "user_uploaded_unverified" == value["source_trust"]
    content=knowledge._db_path().read_bytes()
    assert doc not in content
    assert b"aprendizaje colaborativo" not in content
    found=client.post("/api/sky/knowledge/search",headers=auth(),json={
        "query":"aprendizaje colaborativo","limit":4})
    assert found.status_code==200,found.text
    results=found.json()["results"]
    assert results
    assert "aprendizaje colaborativo" in results[0]["excerpt"]
    assert results[0]["citation"].startswith("sky-doc:")
    assert results[0]["source_trust"]=="user_uploaded_unverified"
    again=client.post(path,headers=auth(),files=f(),data={
        "owner_attested":"true","consent_to_index":"true"})
    assert again.status_code==201
    assert again.json()["status"]=="already_indexed"
    assert again.json()["doc_id"]==value["doc_id"]
    assert len(client.get(path,headers=auth()).json()["documents"])==1
    assert client.delete(path+"/"+value["doc_id"],headers=auth()).json()["deleted"]
    assert client.post("/api/sky/knowledge/search",headers=auth(),json={
        "query":"aprendizaje colaborativo"}).json()["results"]==[]


def test_legacy_upload_optional_learning_does_not_persist_without_optin(client):
    data=b"Curso de programacion de aplicaciones Android y Flutter"
    endpoint="/api/chat/upload"
    basic=client.post(endpoint,headers=auth(),files={
        "file":("curso.txt",data,"text/plain")})
    assert basic.status_code==200,basic.text
    assert basic.json()["doc_id"] is None
    assert basic.json()["knowledge_index_status"]=="not_requested"
    bad=client.post(endpoint,headers=auth(),files={
        "file":("curso.txt",data,"text/plain")},
        data={"remember_document":"true"})
    assert bad.status_code==403
    saved=client.post(endpoint,headers=auth(),files={
        "file":("curso.txt",data,"text/plain")},
        data={"remember_document":"true","owner_attested":"true"})
    assert saved.status_code==200,saved.text
    assert saved.json()["doc_id"].startswith("doc_")
    assert saved.json()["knowledge_index_status"]=="indexed"
    assert saved.json()["learning_performed"] is False


def test_sky_chat_and_voice_search_own_document_without_hallucinating(client):
    doc=b"El proyecto incluye aplicaciones para aprender geometria aplicada y topografia."
    ok=client.post("/api/sky/knowledge/documents",headers=auth(),files={
        "file":("proyecto.txt",doc,"text/plain")},
        data={"owner_attested":"true","consent_to_index":"true"})
    assert ok.status_code==201,ok.text
    prompt="SKY, buscá en mis documentos sobre topografia aplicada"
    res=client.post("/api/asistente/mensaje",headers=auth(),json={"texto":prompt})
    assert res.status_code==200,res.text
    body=res.json()
    assert body["atendido_por"]=="SKY"
    assert body["proveedor"]=="sky-private-knowledge"
    assert "proyecto.txt" in body["mensaje"]
    assert "sky-doc:" in body["mensaje"]
    voice=client.post("/api/asistente/stream",headers=auth(),json={
        "texto":"Sky, consulta en mis documentos sobre topografia","modo":"voz"})
    assert voice.status_code==200,voice.text
    result=json.loads(voice.text.strip().splitlines()[-1])["final"]
    assert result["atendido_por"]=="SKY"
    assert result["knowledge"]["results"]
    assert not result["model_weights_updated"]


def test_no_storage_without_encryption_key(client,monkeypatch):
    monkeypatch.delenv("SKY_NEURAL_MEMORY_KEY",raising=False)
    data=b"Un documento privado con texto bastante largo."
    attempt=client.post("/api/sky/knowledge/documents",headers=auth(),files={
        "file":("secreto.txt",data,"text/plain")},
        data={"owner_attested":"true","consent_to_index":"true"})
    assert attempt.status_code==503
