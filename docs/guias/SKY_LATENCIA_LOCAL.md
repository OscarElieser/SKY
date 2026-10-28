# Medir latencia real de SKY sin gastar cuotas de nube

La respuesta de SKY en Windows tardó **35,8 segundos** con `llama3.2`
en una prueba de conversación local. Una respuesta correcta confirma
conectividad, no velocidad adecuada para voz.

Este módulo compara modelos *ya instalados* en Ollama y la ruta completa
`sky_asistente_personal.atender()`, sin cambiar ningún proveedor
configurado, clave ni archivo `.env`.

## Ejecutar en la PC

```powershell
Set-Location "C:\Users\PC 1\Documents\Desktop\SKY"
git pull --ff-only origin main

# Ollama solo. Compara modelos instalados pequeños y ya descargados.
& .\.venv\Scripts\python.exe -m neural_core.sky_latency_probe --models llama3.2 qwen2.5:3b --skip-full

# Ollama y asistente completo para ambos modelos.
& .\.venv\Scripts\python.exe -m neural_core.sky_latency_probe --models llama3.2 qwen2.5:3b
```

Para evaluar otro modelo instalado, añade `qwen3.5:4b` o
`qwen2.5:7b` a `--models`. No se descarga nada. Modelos grandes pueden
consumir RAM considerable y tardar más.

La utilidad fuerza `SKY_LOCAL_ONLY=1` y `SKY_CEREBRO=subasta`
**solo dentro de su proceso**. Solo envía una pregunta pública fija
sobre fotosíntesis a Ollama local y a SKY. No imprime respuestas, memoria
personal ni credenciales. Las reglas de SKY se ejecutan normalmente;
la utilidad no ordena acciones al dispositivo.

## Cómo leer los resultados

- `Ollama directo (s)`: tiempo de una inferencia local con mensaje corto.
- `Carga / prompt / generacion`: contadores proporcionados por Ollama.
  El valor de `tokens/s` mide velocidad de producción, no calidad.
- `SKY completo (s)`: latencia de la ruta real `atender()`.
- `preparacion_s`: detección de alias aprendidos; `reglas_s`:
  intérpretes, funciones y comprobaciones de seguridad; `agentes_s`:
  subagentes cognitivos solo si la pregunta los amerita;
  `cerebro_s`: prompt completo e inferencia.
- Las etapas son inclusivas y no se deben sumar sin más. Las dos rutas
  tienen prompts de diferente tamaño: su diferencia no es una medición
  pura del tiempo de los módulos.
- El primer modelo puede tardar más por carga en memoria; mide de nuevo
  los candidatos antes de seleccionar un nuevo `OLLAMA_MODEL`.

Si `reglas_s` es alto, optimizar importaciones o heurísticas después de
medir. Si `cerebro_s` domina, comparar consumo de prompt, modelos
pequeños y velocidad de generación. No eliminar reglas, memoria o
controles de seguridad por velocidad.

**Este PR solo añade diagnósticos; no demuestra ninguna mejora de
latencia hasta ejecutar las pruebas en el equipo.**

## Métricas de la inferencia real de SKY

La utilidad también imprime **`Metricas Ollama en SKY`** (tokens del
prompt, tokens generados y segundos de carga/evaluación/generación) extraídos
de la respuesta streaming de la API local. **`Tamano seguro del contexto`**
reporta los caracteres del prompt de sistema y el número de turnos de
historial, pero no incluye su contenido. Estas métricas distinguen un
modelo lento al generar de un prompt demasiado extenso.

Si la respuesta se corta antes de la trama final de Ollama, los contadores
pueden aparecer vacíos; no deben inventarse valores ni atribuirse a la nube.
El diagnóstico no modifica reglas ni límites de respuesta del asistente.


## Contexto ligero opcional para preguntas generales

El diagnóstico de Windows del 28/10/2026 mostró que SKY con `llama3.2`
consumió **28,266 s en evaluar 1337 tokens del prompt**, frente a
11,182 s generando 114 tokens. La mayor oportunidad de mejora es reducir
el contexto enviado a Ollama **solo cuando no sea necesario**.

La optimización `SKY_LOCAL_FAST_CONTEXT=1` es optativa y está desactivada
por defecto. Para peticiones autónomas como «Explica en dos oraciones
que es la fotosintesis» usa instrucciones cortas, sin incorporar datos
personales ni reglas de habilidades que no son relevantes. Conserva el
sistema habitual cuando se usan conversaciones previas, se mencionan
proyectos, archivos, cuentas o información del usuario, o se solicita
realizar acciones. Las API de nube siguen usando siempre el contexto
completo. No altera ninguna memoria ni elimina funciones.

**Prueba A/B sin guardar cambios en .env ni gastar cuotas cloud:**

```powershell
Set-Location "C:\Users\PC 1\Documents\Desktop\SKY"
git pull --ff-only origin main

& .\.venv\Scripts\python.exe -m neural_core.sky_latency_probe --models llama3.2 --skip-direct --full-context
& .\.venv\Scripts\python.exe -m neural_core.sky_latency_probe --models llama3.2 --skip-direct --fast-context
```

Comparar `SKY completo (s)`, `prompt_tokens`, `prompt_s`,
`generation_s`, `system_chars` y que la respuesta siga siendo correcta.
Como el hardware y la memoria varían, repetir en orden inverso si los
resultados parecen inconsistentes.

Solo si compruebas una mejora útil en la PC, activar de forma persistente
`SKY_LOCAL_FAST_CONTEXT=1` dentro del `.env` local. Para revertir,
ajustar a `0` y reiniciar SKY. Las pruebas del repositorio comprueban
que los prompts completos siguen disponibles para memoria, historial,
órdenes y nube. Ninguna optimización de esta ruta elude las autorizaciones
del agente de dispositivo.
