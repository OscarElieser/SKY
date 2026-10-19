# SKY IA v11.0 — Inicio seguro

## ¿Qué es?

SKY IA Universal es una plataforma modular de IA y creatividad. Esta versión amplía la preparación pública sin sustituir las herramientas de imagen/video, metaverso, memoria, Office, proyectos, workflows ni el resto de módulos heredados. La dirección conceptual corresponde a **Oscar Elieser Chamorro Guzmán**.

## Instalación local

1. Extraé el ZIP v11.0 en una carpeta nueva. No sobrescribás una instalación que contenga datos privados.
2. Instalá Python 3.11, FFmpeg y las dependencias de `requirements_studio.txt`. Para entornos reproducibles, utilizá el archivo `requirements_verified_v110.txt` como constraints.
3. Iniciá desde el lanzador local o con la API según el manual anterior. No expongás el puerto HTTP local directamente en Internet.
4. Para Creative Studio, mantené FFmpeg y OpenCV instalados cuando el flujo lo requiera.
5. Las claves y semillas MFA nunca van en el repositorio: usar `deploy/secrets` con permisos restrictivos o un gestor externo de secretos.

## Pruebas locales

```bash
PYTHONPATH=. SKY_CREATIVE_WORKER=0 SKY_WORKFLOWS_ENABLED=0 pytest -q tests
python -m scripts.audit_stack_v109
python scripts/security_audit_v103.py .
```

## Integración real en GitHub Actions

`SKY v11.0 full-stack HTTPS, Redis, recovery and measured multilingual ASR` ejecuta la pila Docker completa con certificado local verificado, Redis autenticado, worker sin conectividad y API sin exposición directa. El ensayo se hace solo contra `127.0.0.1` y se destruyen los contenedores, volúmenes y credenciales sintéticas al finalizar.

### Diagnóstico de voz

El workflow descarga un modelo abierto `faster-whisper-base` a un directorio temporal y sintetiza audios *ficticios* en español, francés e inglés. El reporte contiene WER, idioma y hashes de audio, **sin transcripciones ni archivos de voz**. Que el motor transcriba no demuestra precisión clínica, universal ni preparación comercial. Para hacer fallar el job cuando no llegue al objetivo, elegí manualmente `workflow_dispatch` y `enforce_voice_quality=true`.

### Prueba de recuperación

El script `scripts/ci_cross_container_v109.sh` restaura un respaldo sintético AES-GCM en un contenedor independiente y sin red. Es una simulación de destino diferente, no una copia en una VM o equipo físico remoto.

## Requisitos pendientes para un público global

La implementación de contenedores y sus checks no sustituyen revisión de seguridad, pentest, backups fuera del mismo host, WAF, MFA obligatorio para administradores, registro auditable, aislamiento de uploads y monitorización. No desplegar como servicio público con datos sensibles hasta completar esas etapas.

## Conexión con BAQUEANO

Esta versión no modifica BAQUEANO ni su producción, base de datos, Hosting o DNS. Cualquier integración permanece privada y requiere una autorización independiente.

## Resultados reales de GitHub Actions

En el primer run v11, Docker arrancó los cuatro servicios saludables, Redis autenticado y certificado HTTPS comprobado; ejecutó 60 solicitudes con p95=56,88 ms y cero errores, antes de fallar un auditor de puertos que confundía EXPOSE con publicación en el host. Se corrigió. Las pruebas 3D requieren SciPy y se añadió la dependencia. El modelo Whisper base produjo WER es=1,9000, fr=0,1667, en=0,3333 (sintético); español sigue sin aprobar la prueba de calidad.
