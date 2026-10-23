"""Atomic Redis rate-limiter. Fail closed when explicitly configured for public use."""
from __future__ import annotations
import hashlib,os,time
from .secrets_v107 import get_secret

_REDIS=None

def redis_client():
    global _REDIS
    if _REDIS is not None:return _REDIS
    if not os.getenv('SKY_REDIS_URL'):
        return None
    try:import redis
    except ImportError as exc:raise RuntimeError('Instalá redis para habilitar límites distribuidos') from exc
    password=get_secret('SKY_REDIS_PASSWORD')
    # Secrets from Docker are mounted as files; never print password in health checks.
    options={'password': password} if password else {}
    obj=redis.Redis.from_url(os.environ['SKY_REDIS_URL'],socket_connect_timeout=2,socket_timeout=2,decode_responses=True,**options)
    obj.ping()
    _REDIS=obj
    return obj


def allowed(remote:str, scope:str, *,max_requests:int=90, period:int=60)->bool:
    """Fixed-window distributed check; scoped by IP and endpoint family.

    No user IP is sent anywhere other than the configured private Redis server.
    """
    client=redis_client()
    if client is None:return True
    key='sky:limit:'+scope+':'+hashlib.sha256(remote.encode()).hexdigest()[:24]+':'+str(int(time.time())//period)
    # Lua makes increment+expiry atomic even when many API workers share Redis.
    script="local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n"
    count=client.eval(script,1,key,period+5)
    return int(count)<=max_requests
