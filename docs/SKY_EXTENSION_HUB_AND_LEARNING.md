# SKY Extension Hub + Experience Learning · implementación segura

**Proyecto:** SKY IA independiente, creado y dirigido por Oscar Elieser Chamorro Guzmán, con asistencia técnica de ChatGPT de OpenAI. OpenAI no es propietario ni patrocinador oficial de SKY.

## Qué se conserva

Este cambio está construido encima del `main` actualizado que incorporó el PR #27:
- `SKY CORE`, `metaverse/api.py`, HUD holográfico, voz y texto
- `sky_skill_builder.py` y sus pruebas aisladas, sin ejecutar código externo automáticamente
- Ollama, OpenAlex, Crossref, Firecrawl, OpenRouter, Hugging Face, n8n, Zotero, Wolfram
- Controles SKY SENTINEL, PIN/MFA, parada de emergencia y permisos por dispositivo
- Ciclo de acciones `sky_execution_cycle` con estado `VERIFIED` separado de `DISPATCHED`

No se ha instalado en la computadora del propietario ninguna de las
herramientas de terceros de la imagen. No se activan servidores, VPN, ni procesos
de agentes por tenerlos en un catálogo.

## 1. Extension Hub

`neural_core/sky_extension_hub.py` registra herramientas externas agrupadas por
especialidad y forma de integración: motor propio, API, sidecar opcional,
biblioteca, skill o herramienta de desarrollo. Incluye los doce repositorios de
la imagen: OpenClaw, Hermes, OpenCode, n8n, Firecrawl, Ollama, Agent Skills,
Dify, Open WebUI, Langflow, Claude Code y LangChain, junto con herramientas
académicas y multimedia relevantes.

Los registros muestran **declaraciones de integración**, no resultados de
pruebas físicas ni instalación. Una URL o README recuperado se considera
información no confiable, jamás instrucciones para ejecutar.

### Herramientas invocables en este paquete

Solo las siguientes pasan por un enrutador explícito, con acción acotada y
aprobación de la persona: Semantic Scholar (búsqueda), Zotero (lectura),
Wolfram (cálculo), n8n (lista de flujos y ejecuciones, **no dispara webhooks**),
Firecrawl (extrae de dominios previamente autorizados), Ollama (respuesta
local), OpenRouter y Hugging Face (modelos seleccionados), GitHub (commits).

El Hub reusa los adaptadores existentes de SKY; no descarga ni ejecuta el
código de OpenClaw, Hermes, Dify, Open WebUI o Langflow. Los proveedores que
puedan generar costes requieren el PIN SENTINEL adicional. `SKY_LOCAL_ONLY=1`
bloquea los modelos remotos y demás proveedores externos. n8n permite su
instancia local únicamente si el propietario la autorizó.

API, dentro del servicio SKY protegido:

- `GET /api/sky/extensions` — inventario sin efectos
- `GET /api/sky/extensions/actions` — herramientas invocables y operaciones
- `GET /api/sky/extensions/{extension_id}` — detalle
- `POST /api/sky/extensions/{extension_id}/invoke` — llamada explícita
  con `{"action":"search","arguments":{"query":"aprendizaje"},"approved":true}`

La API no acepta nombres de ejecutables o URL arbitrarias para la invocación.

## 2. Experiencia comprobada: aprender, recordar, repetir

SKY ya contenía memoria, builder y habilidades. Añadimos un mecanismo
separado y muy limitado para convertir **ciclos realmente verificados** en
procedimientos reutilizables. `sky_execution_cycle.export_verified_replay`
rechaza cualquier ciclo no terminado, no verificado o con pasos no permitidos.
Por seguridad inicialmente admite solo comprobación de estado y apertura de
aplicaciones de la lista oficial `AUTHORIZED_APPS`. Rechaza escritura de
texto, archivos, URLs, reproductores, credenciales y cualquier comando de
consola. Las aperturas necesitan identificador de comprobación del agente.

El HUD añade «Recordar procedimiento» **solo al finalizar** un ciclo elegible.
Al guardarlo, SKY solicita el PIN si está configurado. Los datos se almacenan
en `~/.neuralt/sky_verified_procedures.json`, con escritura atómica y permisos
restringidos. Se mantiene un máximo de 40 procedimientos con nombres
únicos; los resultados que repiten exactamente el procedimiento suman una
evidencia adicional. No guarda el texto original dictado ni rutas privadas.

Ejemplo de voz o texto:

> SKY, repetí procedimiento abrir word

SKY crea un **nuevo ciclo READY** sin ejecutar acciones. Cada paso sigue
pidiendo autorización y verificación. El propietario puede visualizar y
eliminar los procedimientos desde el panel «Habilidades»; eliminar exige PIN.

API:

- `GET /api/sky/learning/capabilities`
- `GET /api/sky/learning/procedures`
- `POST /api/sky/learning/capture`: ciclo completo + nombre + `approved=true`; PIN
- `POST /api/sky/learning/procedures/{id}/plan`: plan, no ejecución
- `DELETE /api/sky/learning/procedures/{id}`: `approved=true` + PIN

**Aprender procedimientos no es reentrenar automáticamente los pesos del
modelo.** SKY acumula experiencias verificadas y reutiliza pasos autorizados;
la creación de nuevas skills de Python conserva el sandbox existente y la
aprobación humana. Ningún resultado de un LLM, documento, web o repo permite
autoactualizar el núcleo.

## Cómo probarlo

Para pruebas de sintaxis y lógica:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q tests/test_sky_extension_learning.py tests/test_sky_execution_cycle.py tests/test_sky_skillpack.py
```

En el equipo Windows propietario, una vez instalados la versión y el agente:

1. Abrir el HUD y decir: «SKY, abre Word y luego abre Excel».
2. Autorizar cada acción y **comprobar la apertura real**.
3. Al recibir `VERIFIED` para ambos pasos, usar «Recordar procedimiento».
4. Ponerle nombre, confirmar con el PIN y consultar la memoria en Habilidades.
5. Solicitar: «SKY, repetí procedimiento <nombre>» y comprobar que no se
   ejecuta nada antes de aprobar cada paso.
6. Probar parada de emergencia, un programa no instalado y un ciclo fallido.
7. Verificar que las URLs y textos privados nunca se ofrecen para aprender.
8. Hacer la misma prueba desde Android mediante HTTPS privado. La PWA no es
   una APK con control nativo de Android.

## Siguientes ampliaciones, sujetas a revisión

- Adaptadores verdaderos y aislados para OpenCode y bibliotecas de código;
- importación de skills seleccionadas del formato Agent Skills con comprobación
  de licencias, integridad, permisos y ejecución en sandbox;
- modelos de memoria y consolidación semántica con control del propietario;
- uso optativo de Dify/Langflow/Open WebUI como aplicaciones independientes,
  si las pruebas demuestran una mejora mensurable;
- certificación física PC/Android, latencia, consumo y recuperación.

No se certifica el 100/100 a partir de las pruebas de GitHub: el hardware,
los conectores privados y las plataformas de terceros deberán probarse
en los dispositivos autorizados.
