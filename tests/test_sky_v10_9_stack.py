"""Local contract tests; networked Docker and real ASR run as separate CI jobs."""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import pytest
import yaml
from scripts.audit_stack_v109 import audit
from scripts.cross_host_recovery_v109 import archive_sha256, make_fixture, recover
from neural_core.sky_backup_schedule_v108 import secret_from_file


def key(tmp_path):
    p=tmp_path/'restore-key';p.write_text('a-test-only-long-and-random-placeholder-secret-2026',encoding='utf8');p.chmod(0o600)
    return p


def test_stack_compose_static_security():
    result=audit()
    assert result['static_passed'] and not result['docker_executed'] and not result['remote_host_tested']


def test_compose_only_loopback_tls_host_port():
    cfg=yaml.safe_load((Path(__file__).resolve().parents[1]/'deploy/compose.integration.yml').read_text())
    assert cfg['services']['proxy']['ports']==['127.0.0.1:18443:443']
    for name in ('api','renderer','redis'):
        assert 'ports' not in cfg['services'][name]
    assert cfg['services']['renderer']['network_mode']=='none'


def test_ci_requires_certificate_chain_verification():
    content=(Path(__file__).resolve().parents[1]/'scripts/ci_stack_smoke_v109.sh').read_text()
    assert '--cacert' in content and '--resolve' in content
    assert 'curl -k' not in content and '--insecure' not in content
    assert 'docker compose' in content and 'down --volumes' in content


def test_distributed_limit_redis_is_reachable_only_inside_stack():
    config=yaml.safe_load((Path(__file__).resolve().parents[1]/'deploy/compose.integration.yml').read_text())
    assert config['networks']['internal']['internal'] is True
    assert 'internal' in config['services']['redis']['networks']
    assert config['services']['api']['environment']['SKY_REDIS_URL'].startswith('redis://redis:')
    assert 'sky_redis_password' in config['services']['api']['secrets']


def test_synthetic_backup_restores_into_independent_empty_directory(tmp_path):
    secret=key(tmp_path); backup=tmp_path/'export.skybackup'
    built=make_fixture(backup,secret)
    assert built['encrypted'] and built['files']==2
    target=tmp_path/'new-server'/'restored'
    status=recover(backup,target,secret,built['archive_sha256'])
    assert status['restored_files']==2 and status['source_untouched']
    with sqlite3.connect(target/'db/synthetic.sqlite3') as con:
        assert con.execute('select name from dummy').fetchone()[0]=='restauracion-sintetica'
    assert (target/'media/images/sample.png').read_bytes().startswith(b'\x89PNG')
    assert not status['production_certified']


def test_transfer_checksum_mismatch_rejected_before_creating_dir(tmp_path):
    secret=key(tmp_path);backup=tmp_path/'export.skybackup'
    make_fixture(backup,secret)
    target=tmp_path/'recovered'
    with pytest.raises(ValueError,match='cambió'):
        recover(backup,target,secret,'0'*64)
    assert not target.exists()


def test_wrong_passphrase_rejected_and_not_restored(tmp_path):
    secret=key(tmp_path); backup=tmp_path/'export.skybackup'; built=make_fixture(backup,secret)
    other=tmp_path/'other-key';other.write_text('another-test-only-secret-with-good-length');other.chmod(0o600)
    with pytest.raises(ValueError): recover(backup,tmp_path/'new',other,built['archive_sha256'])
    assert not (tmp_path/'new').exists()


def test_symlink_archive_and_key_rejected(tmp_path):
    secret=key(tmp_path);backup=tmp_path/'export.skybackup';make_fixture(backup,secret)
    link=tmp_path/'symlink.skybackup';link.symlink_to(backup)
    with pytest.raises(ValueError):archive_sha256(link)
    k_link=tmp_path/'key-link';k_link.symlink_to(secret)
    with pytest.raises(ValueError):secret_from_file(k_link)


def test_existing_destination_never_overwritten(tmp_path):
    secret=key(tmp_path);backup=tmp_path/'export.skybackup';built=make_fixture(backup,secret)
    target=tmp_path/'existing';target.mkdir();(target/'private.txt').write_text('keep')
    with pytest.raises(FileExistsError):recover(backup,target,secret,built['archive_sha256'])
    assert (target/'private.txt').read_text()=='keep'


def test_malformed_sha_rejected(tmp_path):
    secret=key(tmp_path);backup=tmp_path/'export.skybackup';make_fixture(backup,secret)
    with pytest.raises(ValueError,match='obligatoria'):
        recover(backup,tmp_path/'new',secret,'...')


def test_github_jobs_are_opt_in_for_voice_weights():
    job=yaml.safe_load((Path(__file__).resolve().parents[1]/'.github/workflows/sky-v109-stack-and-recovery.yml').read_text())
    triggers=job.get('on',job.get(True,{}))
    assert 'workflow_dispatch' in triggers
    assert 'actions/checkout@v4' in str(job)
    assert 'voice-real-model' in job['jobs']
    assert 'workflow_dispatch' in str(job['jobs']['voice-real-model']['if'])


def test_v109_reviewed_security_labels_are_global():
    from neural_core.sky_global_ui import glossary
    for lang in ('en','pt','fr','de','it','ar','zh','ja','sw'):
        entries=glossary(lang)
        assert entries['Certificado verificado'].strip()
        assert entries['Reconocimiento de voz real'] != 'Reconocimiento de voz real'
