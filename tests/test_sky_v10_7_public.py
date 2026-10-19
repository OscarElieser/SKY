"""SKY v10.7: no Docker needed for static deploy security assertions.

Passing these checks never implies containers were run or a pentest passed.
"""
from __future__ import annotations
import base64
from pathlib import Path
import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]


def test_secret_reader_inline_and_file(tmp_path,monkeypatch):
    from metaverse.secrets_v107 import get_secret
    path=tmp_path/'token';path.write_text(' example-key \n')
    monkeypatch.delenv('SKY_API_KEY',raising=False)
    monkeypatch.setenv('SKY_API_KEY_FILE',str(path))
    assert get_secret('SKY_API_KEY')=='example-key'
    monkeypatch.setenv('SKY_API_KEY','second-secret')
    with pytest.raises(RuntimeError,match='nunca ambos'):get_secret('SKY_API_KEY')
    monkeypatch.delenv('SKY_API_KEY',raising=False)
    link=tmp_path/'link';link.symlink_to(path)
    monkeypatch.setenv('SKY_API_KEY_FILE',str(link))
    with pytest.raises(RuntimeError):get_secret('SKY_API_KEY')


def test_secret_reader_fails_if_insecure_content(tmp_path,monkeypatch):
    from metaverse.secrets_v107 import get_secret
    p=tmp_path/'bad';p.write_text('a\nb\n')
    monkeypatch.setenv('SKY_OWNER_MFA_SECRET_FILE',str(p))
    monkeypatch.delenv('SKY_OWNER_MFA_SECRET',raising=False)
    with pytest.raises(RuntimeError):get_secret('SKY_OWNER_MFA_SECRET')
    p.write_text(''*1 + 'x'*5000)
    with pytest.raises(RuntimeError):get_secret('SKY_OWNER_MFA_SECRET')


def test_owner_key_and_totp_read_from_file(tmp_path,monkeypatch):
    from metaverse.api import api_token
    from metaverse import owner_mfa
    key=tmp_path/'key';key.write_text('x'*44)
    seed=tmp_path/'mfa';seed.write_text(base64.b32encode(b'1'*32).decode('ascii')+'\n')
    monkeypatch.delenv('SKY_API_KEY',raising=False)
    monkeypatch.delenv('SKY_OWNER_MFA_SECRET',raising=False)
    monkeypatch.setenv('SKY_API_KEY_FILE',str(key))
    monkeypatch.setenv('SKY_OWNER_MFA_SECRET_FILE',str(seed))
    assert api_token()=='x'*44
    assert owner_mfa.required()
    assert owner_mfa.verify(owner_mfa.code_at(100000),now=100000)


def test_secrets_provision_no_overwrite_or_log(tmp_path):
    from scripts.provision_secrets_v107 import provision
    target=tmp_path/'vault'
    status=provision(target)
    assert len(status['created'])==4
    assert 'redis.conf' in status['created']
    assert 'requirepass ' in (target/'redis.conf').read_text()
    assert 'redis.conf' not in str(status.get('directory'))
    assert (target/'sky_api_key.txt').stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):provision(target)


def test_compose_static_isolation_policy():
    config=yaml.safe_load((ROOT/'deploy/compose.yml').read_text())
    services=config['services'];assert {'api','renderer','redis','proxy'}.issubset(services)
    for name in ('api','renderer','redis'):
        service=services[name]
        assert service.get('read_only') is True
        assert service.get('cap_drop')==['ALL']
        assert 'no-new-privileges:true' in service.get('security_opt',[])
        assert 'ports' not in service
    assert services['renderer']['network_mode']=='none'
    assert services['api']['environment']['SKY_CREATIVE_WORKER']=='0'
    assert services['api']['environment']['SKY_WORKFLOWS_ENABLED']=='0'
    assert services['api']['environment']['SKY_API_KEY_FILE'].startswith('/run/secrets/')
    assert config['networks']['backend']['internal'] is True
    assert services['proxy']['ports']==['80:80','443:443']


def test_deployment_guard_requires_owner_secret_file(tmp_path,monkeypatch):
    from metaverse.deployment_v102 import validate_environment
    monkeypatch.setenv('SKY_DEPLOYMENT_MODE','public')
    monkeypatch.setenv('SKY_TRUSTED_HOSTS','sky.example.com')
    monkeypatch.delenv('SKY_OWNER_MFA_SECRET',raising=False)
    monkeypatch.setenv('SKY_OWNER_MFA_SECRET_FILE',str(tmp_path/'not-exist'))
    with pytest.raises(RuntimeError):validate_environment()


def test_disaster_recovery_drill_synthetic_and_tamper():
    from scripts.disaster_recovery_v107 import exercise
    status=exercise(passphrase='strong-test-only-passphrase-2026')
    assert status['passed'] and status['tampering_rejected']
    assert status['invalid_password_rejected'] and status['live_data_unchanged']
    assert status['production_disaster_recovery_certified'] is False


def test_transcription_audit_without_model_never_claims_real_result(monkeypatch):
    from scripts.audit_voice_model_v107 import audit
    from neural_core import sky_stt_local
    monkeypatch.setattr(sky_stt_local,'capabilities',lambda:{'available':False})
    monkeypatch.setattr(sky_stt_local,'model_directory',lambda:None)
    status=audit()
    assert not status['real_transcription_tested'] and not status['model_available']
    assert 'wer' not in status and status['network_requests']==0


def test_transcription_requires_audio_and_reference():
    from scripts.audit_voice_model_v107 import audit
    with pytest.raises(ValueError,match='juntos'):audit(reference='hola')


def test_labels_added_to_multiple_language_glossaries():
    from neural_core.sky_global_ui import glossary
    for lang in ('en','pt','fr','ar','zh','ja','sw'):
        for label in ('Acceso SKY','Chat del mundo','Comprobar módulos'):
            assert glossary(lang)[label] != label
    assert glossary('ar')['Acceso SKY'].startswith('الدخول')


def test_ui_static_coverage_improves_for_multiple_languages():
    from neural_core.sky_i18n_audit import report
    r=report(ROOT/'metaverse'/'static')
    assert r['visible_static_labels']>=500
    for language,minimum in [('en',128),('pt',118),('fr',118),('ar',113),('zh',111),('ja',111),('sw',98)]:
        assert r['languages'][language]['translated']>=minimum
        assert r['languages'][language]['percent']<100


def test_dockerignore_excludes_local_private_storage():
    text=(ROOT/'.dockerignore').read_text()
    assert 'deploy/secrets/' in text and 'local_data/' in text and '.env' in text
    assert not (ROOT/'deploy/secrets/sky_api_key.txt').exists()
