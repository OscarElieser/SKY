# SKY IA v10.0 — Preparación para producción (no certificación)

**Dirección del proyecto:** Oscar Elieser Chamorro Guzmán.

## Lo comprobado localmente

- 185 pruebas automatizadas pasan, incluido un video con seguimiento y superposiciones reales.
- Hay un microbenchmark aislado de la ruta autenticada de capacidades (`python scripts/benchmark_sky_v10.py`). Es solo un ensayo de concurrencia básico; no equivale a tráfico real público.
- El motor FFmpeg realiza trabajos en cola con versiones bloqueadas y estado persistente; conviene separar el worker de la API antes del despliegue público.

## Requisitos antes de usuarios públicos

1. **Acceso:** identidad del creador basada en cuenta autenticada + segundo factor; no depender de una clave maestra compartida entre usuarios. La herramienta BAQUEANO solo visible y autorizada al propietario.
2. **Red:** TLS, protección DDoS, límite de solicitudes e inspección de cargas. Nunca exponer el endpoint privado directamente con HTTP.
3. **Datos:** PostgreSQL con copias verificadas; almacenar videos y assets en Storage con URLs firmadas; RLS real por usuario. No usar una sola SQLite para tráfico masivo.
4. **Video:** separar renderizadores FFmpeg con colas persistentes, cuotas, límites de CPU/RAM/disco, limpieza de medios y revisión de códecs vulnerables.
5. **Seguridad:** secrets del proveedor gestionados fuera del repositorio, registros de auditoría, autorización por proyecto y control de contenido subido.
6. **Calidad:** benchmark con tráfico externo (p50/p95/p99), pruebas de recuperación ante caída, tests E2E móvil/escritorio y validación real de Gemini con credenciales que no se registren en logs.
7. **GitHub:** ejecución de CI en cada cambio, revisión de dependencias, ramas protegidas y estrategia de reversión antes del despliegue.

## Gemini real

La ruta `POST /api/creative/gemini/check` realiza una llamada real únicamente cuando el creador la solicita y la clave está configurada localmente. No se verificó con proveedor externo durante la creación de v10.0; no afirmarlo como validado.

## Infraestructura prevista

Preparar Hostinger + Cloudflare como servicios de dominio/distribución según los recursos contratados; Supabase para datos/Storage autorizados, Firebase para compatibilidad según la arquitectura elegida y GitHub para control de código. No asumir que existe ya despliegue público ni que un plan concreto soporta procesos persistentes de FFmpeg.