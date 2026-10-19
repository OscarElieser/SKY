# SKY IA v10.6 — Global Voice & Production Readiness

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

## Cambios implementados

1. **Reconocimiento de voz local por proceso separado.** `sky_stt_isolated_v106.py` normaliza WAV con FFmpeg, valida idioma, inicia un worker Python dedicado sin pasar tokens API ni secretos de SKY al entorno hijo, prohíbe descargas remotas de modelos y limita su ejecución a 100 segundos. Los fallos se muestran sin revelar `stderr`, archivos privados ni detalles de la instalación. No implica una sandbox del sistema operativo: para modo público falta contenedor aislado sin permisos.
2. **Prueba reproducible de precisión real**, `python -m scripts.validate_local_voice_v106 --audio ... --expected ...`, que calcula WER y **falla si no hay un modelo local instalado**; no genera resultados simulados de transcripción.
3. **Ensayo de recuperación cifrada aislado** (`python -m neural_core.sky_recovery_drill_v106`): comprueba respaldo AES-GCM de SQLite y media, verificación SHA-256, extracción fuera de producción, integridad SQLite y conservación de archivos origen, destruyendo la carpeta temporal al terminar. Por defecto utiliza datos sintéticos; `--installed` requiere detener SKY y disponer de la contraseña, y solo cubre fuentes explícitamente admitidas.
4. **Etiquetas de interfaz revisadas en nueve idiomas**: 27 etiquetas más para inglés, portugués, francés, alemán, italiano, árabe, chino, japonés y suajili. Los idiomas sin cobertura siguen marcados como parciales, no como traducciones completas.
5. **CI y pruebas**, con nueve regresiones adicionales para acceso privado, aislamiento de claves, timeout, fallos de worker, cálculos WER, restauración real y traducciones verificadas.

## Validación local — 19 de octubre de 2026

- `PYTHONPATH=. pytest -q --disable-warnings`: **233 pruebas aprobadas** (224 heredadas, 9 nuevas).
- Escaneo `scripts/security_audit_v103.py`: **313 archivos**, 0 coincidencias de sus reglas; no es un pentest ni una auditoría externa.
- `node --check metaverse/static/creative.js`: sintaxis correcta.
- Ensayo con contraseña temporal: respaldo y restauración cifrados correctos, sin alterar las fuentes.
- `faster-whisper` y modelo CTranslate2 local: **no instalados** en este entorno. Validación de una transcripción real: **pendiente**. El comprobador retorna estado `tested=false`.

## Límites

El aislamiento de procesos no constituye aislamiento de kernel o contenedor. No hay certificación de producción, gestión centralizada de secretos, evaluación de penetración externa ni cobertura total de los 90 idiomas. Ningún archivo o recurso de BAQUEANO fue modificado.
