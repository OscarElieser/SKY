"""SKY v11.0: security, process health, genuine TLS and honest ASR status."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import pytest
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from scripts.renderer_health_v110 import worker_alive
from scripts.ci_https_load_v110 import measure
from scripts.summarize_voice_v110 import summarize, main as voice_summary_main
from scripts.benchmark_voice_multilingual_v108 import main as benchmark_main
from scripts.audit_stack_v109 import audit

ROOT=Path(__file__).resolve().parents[1]


def test_compose_worker_check_has_no_network_dependency():
    for rel in ('deploy/compose.integration.yml','deploy/compose.yml'):
        cfg=yaml.safe_load((ROOT/rel).read_text())['services']
        probe=cfg['renderer']['healthcheck']
        assert probe['test']==['CMD','python','-m','scripts.renderer_health_v110']
        assert cfg['renderer']['network_mode']=='none'
        assert 'ports' not in cfg['renderer']
        assert cfg['api']['healthcheck'] if 'healthcheck' in cfg['api'] else True
    assert audit()['static_passed']


def test_process_health_rejects_missing_worker(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();(proc/'100').mkdir();(proc/'100'/'cmdline').write_bytes(b'python\0-c\0x=\"sky_render_worker.py\"\0')
    assert not worker_alive(proc,exclude_pid=999)


def test_process_health_accepts_python_worker(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();(proc/'101').mkdir();(proc/'101'/'cmdline').write_bytes(b'/usr/local/bin/python\0sky_render_worker.py\0')
    assert worker_alive(proc,exclude_pid=999)
    assert not worker_alive(proc,exclude_pid=101)


def test_process_health_handles_inaccessible_process(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();(proc/'100').mkdir()
    assert not worker_alive(proc,exclude_pid=999)


def test_workflow_covers_reader_and_pin_and_manual_quality():
    workflow=(ROOT/'.github/workflows/sky-v109-stack-and-recovery.yml').read_text()
    assert 'openpyxl' in workflow and 'opencv-python-headless' in workflow
    assert 'numpy==2.3.5' in workflow and 'trimesh==4.11.1' in workflow
    assert 'faster-whisper-base' in workflow
    assert '--report-only' in workflow
    assert 'inputs.enforce_voice_quality == true' in workflow


def test_integration_script_requires_real_tls_and_process_health():
    content=(ROOT/'scripts/ci_stack_smoke_v109.sh').read_text()
    assert '--cacert' in content and '--resolve' in content
    assert '--insecure' not in content and 'curl -k' not in content
    assert 'docker inspect' in content and 'renderer' in content
    assert 'scripts.ci_https_load_v110' in content


def test_voice_summary_preserves_failing_quality():
    report={'tested':True,'actual_transcriptions':3,'all_within_target':False,
            'threshold_wer':0.8,'results_without_transcripts':[
                {'language':'es','wer':0.9},{'language':'fr','wer':0.75},{'language':'en','wer':0.3333}]}
    res=summarize(report)
    assert res['real_inference'] and not res['accuracy_gate_passed']
    assert not res['model_certified']
    assert res['language_wer']['es']==0.9


def test_voice_summary_manual_gate_requires_quality(tmp_path):
    report={'tested':True,'actual_transcriptions':2,'all_within_target':False,
            'threshold_wer':0.8,'results_without_transcripts':[
                {'language':'es','wer':0.9},{'language':'en','wer':0.2}]}
    p=tmp_path/'report.json';p.write_text(json.dumps(report))
    assert voice_summary_main([str(p)])==0
    assert voice_summary_main([str(p),'--enforce'])==2
    with pytest.raises(ValueError):summarize({'tested':False})


def test_voice_runner_skips_uninstalled_model_even_report_only(tmp_path):
    manifest=tmp_path/'manifest.json';data=tmp_path/'voice';data.mkdir()
    for locale in ('es','en'):
        (data/f'{locale}.wav').write_bytes(b'WAV'*500)
    manifest.write_text(json.dumps([{'file':f'{locale}.wav','language':locale,'reference':'hello sky'} for locale in ('es','en')]))
    # Never contacts network; absence of actual model cannot be a success.
    import scripts.benchmark_voice_multilingual_v108 as v
    original=v.capabilities
    v.capabilities=lambda:{'available':False}
    try:
        assert benchmark_main(['--manifest',str(manifest),'--audio-dir',str(data),'--report-only'])==2
    finally:v.capabilities=original


def _server_and_certificate(tmp_path,hostname='sky.test'):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,hostname)])
    now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
          .public_key(key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now-timedelta(hours=1)).not_valid_after(now+timedelta(days=2))
          .add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname)]),critical=False)
          .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True)
          .sign(key,hashes.SHA256()))
    cert_path=tmp_path/'cert.pem';key_path=tmp_path/'key.pem'
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.TraditionalOpenSSL,serialization.NoEncryption()))
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body=b'{"status":"ok"}'
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*a):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path,key_path)
    server.socket=ctx.wrap_socket(server.socket,server_side=True)
    worker=Thread(target=server.serve_forever,daemon=True);worker.start()
    return cert_path,server


def test_real_https_load_checks_hostname_and_certificate(tmp_path,monkeypatch):
    cert,server=_server_and_certificate(tmp_path)
    import scripts.ci_https_load_v110 as m
    original=socket.create_connection
    monkeypatch.setattr(m.socket,'create_connection',lambda address,timeout=8: original(('127.0.0.1',server.server_address[1]),timeout=timeout))
    try:
        result=measure(cert,requests=12,concurrency=3)
        assert result['errors']==0 and result['tls_peer_verified']
        assert result['requests']==12 and not result['production_capacity_proven']
    finally:server.shutdown();server.server_close()


def test_real_https_load_rejects_wrong_hostname(tmp_path,monkeypatch):
    cert,server=_server_and_certificate(tmp_path,'wrong.test')
    import scripts.ci_https_load_v110 as m
    original=socket.create_connection
    monkeypatch.setattr(m.socket,'create_connection',lambda address,timeout=8: original(('127.0.0.1',server.server_address[1]),timeout=timeout))
    try:
        result=measure(cert,requests=3,concurrency=1)
        assert result['errors']==3
    finally:server.shutdown();server.server_close()


def test_https_load_rejects_too_many_requests(tmp_path):
    cert=tmp_path/'cert.pem';cert.write_text('garbage')
    with pytest.raises(ValueError):measure(cert,requests=1000,concurrency=1)


def test_v11_version_and_isolated_drill_are_retained():
    # v11.1+ y v12 conservan todo lo verificado en v11.0.
    assert tuple(int(x) for x in (ROOT/'VERSION.txt').read_text().strip().split('.')[:2]) >= (11, 0)
    script=(ROOT/'scripts/ci_cross_container_v109.sh').read_text()
    assert '--network none' in script and '--read-only' in script
    assert '--expected-sha256' in script


def test_compose_exposed_ports_are_not_published():
    from scripts.ci_exposure_audit_v110 import verify
    config=[{'Service':n,'Publishers':[{'TargetPort':8765,'PublishedPort':0}]} for n in ('api','renderer','redis')]
    config.append({'Service':'proxy','Publishers':[{'TargetPort':443,'PublishedPort':18443}]})
    assert verify(config)['verified']


def test_compose_rejects_actually_published_internal_port():
    from scripts.ci_exposure_audit_v110 import verify
    config=[{'Service':n,'Publishers':[]} for n in ('api','renderer','redis','proxy')]
    config[0]['Publishers']=[{'TargetPort':8765,'PublishedPort':8765}]
    with pytest.raises(ValueError,match='Puerto de host inesperado'):
        verify(config)


def test_compose_audit_accepts_json_lines_and_array():
    from scripts.ci_exposure_audit_v110 import parse, verify
    config=[{'Service':n,'Publishers':[]} for n in ('api','renderer','redis','proxy')]
    assert verify(parse('\n'.join(json.dumps(x) for x in config)))['verified']
    assert verify(parse(json.dumps(config)))['verified']


def test_trimesh_scipy_and_ci_exposure_audit_dependencies_declared():
    assert 'scipy>=1.13,<2' in (ROOT/'requirements_studio.txt').read_text()
    assert 'scipy==1.17.0' in (ROOT/'requirements_verified_v110.txt').read_text()
    assert 'scripts.ci_exposure_audit_v110' in (ROOT/'scripts/ci_stack_smoke_v109.sh').read_text()
