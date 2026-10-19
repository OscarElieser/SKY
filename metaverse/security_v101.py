"""Defense in depth for the private SKY API. Not a replacement for TLS/auth gateway."""
from __future__ import annotations
import os,time,threading
from collections import defaultdict,deque
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

_LOCK=threading.Lock()
_ATTEMPTS=defaultdict(deque)
_WINDOW=300
_MAX_FAILURES=80

def install(app):
    hosts=[x.strip() for x in os.getenv('SKY_TRUSTED_HOSTS','localhost,127.0.0.1,testserver').split(',') if x.strip()]
    if '*' in hosts:raise RuntimeError('SKY_TRUSTED_HOSTS no puede permitir comodín general')
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=hosts,www_redirect=False)
    # TLS deployment is configured on reverse proxy. Do not trust arbitrary
    # X-Forwarded-For/Proto headers from a direct client.

    @app.middleware('http')
    async def secure_response(request:Request,call_next):
        path=request.url.path
        # Protect state changes when browsers include an Origin header.
        if request.method in ('POST','PUT','PATCH','DELETE') and request.headers.get('origin'):
            from urllib.parse import urlsplit
            origin=request.headers['origin']
            host=request.headers.get('host','')
            try:origin_host=urlsplit(origin).netloc
            except ValueError:origin_host=''
            if origin_host != host:
                return JSONResponse({'detail':'Origen no autorizado'},status_code=403)
        if os.getenv('SKY_DEPLOYMENT_MODE')=='public' and os.getenv('SKY_BEHIND_TLS_PROXY')=='1':
            # Only valid when a trusted TLS reverse proxy sets the ASGI scheme.
            if request.url.scheme!='https':
                return JSONResponse({'detail':'HTTPS obligatorio'},status_code=403)
        if path.startswith(('/api/','/v1/')):
            try:
                from .distributed_limits import allowed
                remote=request.client.host if request.client else 'unknown'
                rate=20 if path.startswith(('/api/community/login','/api/security/owner-mfa/')) else 90
                if not allowed(remote,'login' if rate==20 else 'api',max_requests=rate):
                    return JSONResponse({'detail':'Cuota temporal alcanzada'},status_code=429,headers={'Retry-After':'60'})
            except Exception:
                # A broken Redis must not silently disable abuse protection for public SKY.
                if os.getenv('SKY_DEPLOYMENT_MODE')=='public':
                    return JSONResponse({'detail':'Limitador de solicitudes no disponible'},status_code=503)
        if path.startswith('/api/') or path.startswith('/v1/'):
            content_length=request.headers.get('content-length')
            if content_length:
                try:size=int(content_length)
                except ValueError:size=-1
                if size<0 or size>120*1024*1024:
                    return JSONResponse({'detail':'Carga demasiado grande'},status_code=413)
            is_json=request.headers.get('content-type','').startswith('application/json')
            allowed_bytes=2*1024*1024 if is_json else 90*1024*1024
            if content_length and int(content_length)>allowed_bytes:
                return JSONResponse({'detail':'Solicitud excede el límite permitido'},status_code=413)
            if request.method in ('POST','PUT','PATCH') and not content_length:
                # Bound transfer-encoded requests that omit Content-Length.
                chunks=[];received=0
                async for chunk in request.stream():
                    received+=len(chunk)
                    if received>allowed_bytes:
                        return JSONResponse({'detail':'Carga excede el límite permitido'},status_code=413)
                    chunks.append(chunk)
                request._body=b''.join(chunks)
        # Failed-auth throttle is intentionally best effort; distributed
        # limits belong in gateway/Redis. Identity never uses untrusted XFF.
        ip=request.client.host if request.client else 'unknown'
        key=(ip,'owner')
        with _LOCK:
            dq=_ATTEMPTS[key];now=time.monotonic()
            while dq and now-dq[0]>_WINDOW:dq.popleft()
            blocked=len(dq)>=_MAX_FAILURES
        if blocked and (path.startswith('/api/') or path.startswith('/v1/')):
            return JSONResponse({'detail':'Demasiados intentos de acceso'},status_code=429,headers={'Retry-After':'300'})
        response=await call_next(request)
        if response.status_code==401 and (path.startswith('/api/') or path.startswith('/v1/')):
            with _LOCK:_ATTEMPTS[key].append(time.monotonic())
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Cross-Origin-Resource-Policy']='same-origin'
        response.headers['Permissions-Policy']='camera=(self), microphone=(self), geolocation=(), payment=()'
        response.headers['Content-Security-Policy']=("default-src 'self'; base-uri 'none'; object-src 'none'; "
            "script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' blob: data:; media-src 'self' blob:; "
            "font-src 'self' data:; connect-src 'self' ws: wss:; "
            "form-action 'self'; frame-ancestors 'none'")
        if path.startswith(('/api/','/v1/','/owner/')):
            response.headers['Cache-Control']='private, no-store'
        if request.url.scheme=='https':
            response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
        return response
