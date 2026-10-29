# SKY IA — núcleo ampliado, memoria, pruebas y entrenamiento propio
Fecha: 28/10/2026. Rama de integración: `main`. Este cambio es aditivo.

## Android: capacidades implementadas en código

**Modelos:** `SkyGeminiModes.kt` define modo económico Gemini 3.5 Flash-Lite,
equilibrado Gemini 3.8 Flash y profundo Gemini 3.1 Pro Preview. Desde Ajustes hay
selector de modelo *por consulta*, además de las órdenes `Modo flash: ...`
y `Modo profundo: ...`. No se cobra ni consulta un modelo más caro silenciosamente:
los modos diferentes al económico requieren selección expresa y una clave de
Gemini válida con cuota. Los identificadores son los publicados en la API.
La prioridad previa de Groq NO intercepta modos Gemini solicitados expresamente.

**Contexto:** `MainActivity.kt` conserva hasta 80 mensajes de la sesión
en memoria; `SkyPhoneCloud.kt` pasa hasta 8 entradas al modelo económico,
14 al Flash y 30 al profundo, sin prometer contexto infinito. Si se marca
en Privacidad «Nube autorizada para ESTE mensaje e historial», es posible
recuperar hasta 40 registros guardados en SQLite y seleccionar después
el tramo que admita el proveedor. Sin la casilla, no se recupera automáticamente
el histórico antiguo para enviarlo a un proveedor. El campo de entrada
admite consultas largas; las cuotas, tokens y ventana real dependen del modelo.

**Memoria de largo plazo:** `SkyLongTermMemory.kt` añade una base SQLite
local, separada del perfil anterior y del historial. La frase autorizada
`recuerda que ...` persiste un hecho expresamente indicado por el usuario.
SKY puede recuperar recuerdos por coincidencia local de palabras y el propietario
puede consultarlos y eliminarlos uno a uno en Ajustes → Mi memoria.
La memoria nueva *no* se envía a Gemini/Groq a menos que el propietario marque
«Enviar datos privados ... para ESTE mensaje». El perfil previo permanece
sin borrado ni migración destructiva. No se guardan pesos de modelos ni se
asume reentrenamiento por recordar. SQLite está protegido por el sandbox
Android pero no incorpora cifrado SQLCipher adicional; evitar guardar secretos.

**Archivos:** el flujo `SkyAttachmentBatch.kt` + `SkyGeminiFiles.kt` conserva
cargas por bloques de hasta 5 archivos, 100 MiB cada uno y 300 MiB combinados,
con PDF limitado a 50 MiB, lectura parcial de Office, permiso explícito,
eliminación remota solicitada y reporte de fallos de borrado. Se agrega
trazabilidad por nombre de los archivos preparados o leídos; *preparado*
no demuestra que todas las conclusiones semánticas de Gemini sean correctas.
No hay acceso universal sin límites a cualquier tipo de archivo.

**Verificación real:** `SkyActionEvidence.kt` guarda resultados locales
diferenciando solicitudes aceptadas por Android (`ENVIADA_SIN_VERIFICAR`),
fallos, rechazos y cambios locales confirmados. Integrado con el
lanzador de aplicaciones, acciones nativas, música y agente remoto.
El panel Ajustes → Evidencias permite ver/eliminar recibos. Solicitar música
no equivale a verificar que suena. Las respuestas sobre hechos recientes
requieren metadatos reales de búsqueda web y enlaces; aun así el usuario debe
evaluar las afirmaciones de las fuentes. No hay acceso irrestricto a otras apps.

## Entrenamiento real del Transformer experimental propio

`neural_core/sky_tiny_transformer.py` es un **modelo nuevo causal de bytes**
con embeddings, posiciones, atención causal multi-cabeza, bloques Transformer,
proyección de vocabulario y optimizador AdamW. Entrena pesos desde cero
con dataset JSONL local aprobado. Esta prueba experimental es deliberadamente
pequeña: NO es Gemini, no razona a nivel fundacional y NO sustituye ningún
modelo de Android ni Windows. El entrenamiento no se ejecuta por abrir SKY,
no se activa automáticamente y el checkpoint debe quedar **fuera del repositorio**.

### Preflight local sin entrenamiento

```bash
python -m neural_core.sky_tiny_transformer --preflight --device cpu \
  --dataset data/training/sky_seed_v1.jsonl --output /tmp/sky-training-cpu
```

### Entrenamiento real controlado en CPU

```bash
python -m neural_core.sky_tiny_transformer --device cpu \
  --dataset data/training/sky_seed_v1.jsonl \
  --output /tmp/sky-tiny-cpu-v1 --steps 20 --context 64 --confirm-rights
```

Requiere PyTorch. Guarda pesos locales en `sky_tiny_transformer.pt`
y métricas observadas del conjunto separado en `manifest.json`. El
resultado siempre queda marcado `active_in_android=false` y
`not_production_ready=true`. No se publican pesos, datos ni claves.

### Entrenamiento en TPU física (solo con infraestructura existente)

En un entorno Linux TPU realmente habilitado, con versiones compatibles de
`torch`/`torch_xla` y `PJRT_DEVICE=TPU`, ejecutar la misma orden con
`--device tpu`. El código selecciona XLA, comprueba que el hardware
sea TPU, usa `xm.optimizer_step` y rechaza explícitamente una TPU ficticia
o una CPU/XLA rotulada falsamente TPU. Se limita a un dispositivo por
proceso; no incluye orquestación multinodo ni creación de máquinas TPU.
La TPU pertenece al proveedor de la infraestructura, no al teléfono.

Documentación: https://docs.pytorch.org/xla/master/ y
https://ai.google.dev/gemini-api/docs/models

## Validación y límites de verificación

- `SkyGeminiModesTest.kt`, `SkyLongTermMemoryTest.kt` y
  `SkyActionEvidenceTest.kt`: lógica de selección, recuperación y estados.
- `tests/test_sky_tiny_transformer.py`: requiere PyTorch para ejecutar
  un paso real en CPU, comprobar máscara causal y proteger checkpoints.
- `.github/workflows/sky-tiny-transformer.yml`: prueba automatizada,
  sin acceso al teléfono ni a una TPU física.
- `SKY Mobile Android Agent` y `SKY Android Signed Release Candidate`:
  compilan, prueban y firman cuando GitHub Actions lo confirme.
  **Que el código esté en main no prueba que una APK nueva esté descargable**.
- Sin pruebas en Samsung real no se puede certificar permisos, micrófono,
  funcionamiento bloqueado, conectividad, ejecución final en otras apps,
  Google Play Protect ni latencia real. No inventar resultados.

Nada de lo anterior requiere borrar SKY Windows, sus agentes, bases de datos,
proveedores ni funcionalidades ya existentes.
