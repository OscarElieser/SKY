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
        if path.startswith('/api/') or path.startswith('/v1/'):
            content_length=request.headers.get('content-length')
            if content_length:
                try:size=int(content_length)
                except ValueError:size=-1
                if size<0 or size>120*1024*1024:
                    return JSONResponse({'detail':'Carga demasiado grande'},status_code=413)
            if request.headers.get('content-type','').startswith('application/json') and content_length and int(content_length)>2*1024*1024:
                return JSONResponse({'detail':'JSON demasiado grande'},status_code=413)
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
