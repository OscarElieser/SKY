"""Conservative public deployment guardrails. Does not certify readiness."""
from __future__ import annotations
import os


def validate_environment():
    mode=os.getenv('SKY_DEPLOYMENT_MODE','local').strip().lower()
    if mode not in ('local','public'):raise RuntimeError('SKY_DEPLOYMENT_MODE debe ser local o public')
    if mode=='local':return {'mode':'local','public_ready':False}
    hosts={x.strip() for x in os.getenv('SKY_TRUSTED_HOSTS','').split(',') if x.strip()}
    if not hosts or hosts.issubset({'localhost','127.0.0.1','testserver'}):
        raise RuntimeError('Modo público necesita SKY_TRUSTED_HOSTS con dominio propio')
    if '*' in hosts:raise RuntimeError('El modo público prohíbe hosts universales')
    api_key=os.getenv('SKY_API_KEY','').strip()
    if len(api_key)<32:
        raise RuntimeError('El modo público requiere SKY_API_KEY explícita de 32 caracteres o más')
    if not os.getenv('SKY_OWNER_MFA_SECRET'):
        raise RuntimeError('El modo público requiere MFA TOTP para el creador')
    from .owner_mfa import validate_configuration
    validate_configuration()
    if api_key==os.getenv('SKY_OWNER_MFA_SECRET','').strip():
        raise RuntimeError('SKY_API_KEY y SKY_OWNER_MFA_SECRET deben ser secretos distintos')
    if not os.getenv('SKY_REDIS_URL'):
        raise RuntimeError('El modo público requiere Redis para limitación distribuida')
    if os.getenv('SKY_BEHIND_TLS_PROXY') != '1':
        raise RuntimeError('El modo público requiere proxy HTTPS verificado')
    if os.getenv('SKY_CREATIVE_WORKER','1') != '0':
        raise RuntimeError('El modo público requiere separar el proceso de render')
    try:
        from .distributed_limits import redis_client
        redis_client()
    except Exception as exc:
        raise RuntimeError('Redis obligatorio no disponible; se bloquea el despliegue público') from exc
    return {'mode':'public','public_ready':False,'requires_external_audit':True}
