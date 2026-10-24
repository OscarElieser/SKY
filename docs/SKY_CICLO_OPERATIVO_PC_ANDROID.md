# SKY IA · Ciclo operativo verificable y cliente instalable Windows/Android

**Rama de integración:** `feat/sky-operational-cycle-mobile-20261023`. Se creó
desde `feat/skillpack-integraciones-reales-20261023`, para conservar el
Skillpack anterior. El archivo `main` y la instalación del propietario
permanecen sin cambios.

## Qué se construyó

La interfaz HUD conserva su núcleo holográfico y añade una ruta de conversación
para órdenes secuenciales por voz y texto. Por ejemplo:

«SKY, abre Word y luego abre Excel».

1. SKY convierte ambos comandos con su intérprete de acciones existente.
2. La API crea un ciclo de hasta seis pasos, sin ejecutar ninguno todavía.
3. El HUD solicita autorización para el paso actual.
4. SKY utiliza `agente_dispositivo.py`, con su política de capacidades y
   autenticación ya existentes.
5. Solo marca `VERIFIED` cuando el agente confirma observación; `SENT`,
   `RUNNING` o `PENDING` pasan a `DISPATCHED` y bloquean pasos siguientes.
6. Si el agente devuelve un identificador, el HUD permite solicitar una nueva
   verificación física sin reejecutar el comando.
7. Un resultado fallido, una parada de emergencia o la cancelación del usuario
   bloquean los siguientes pasos.

La API mantiene el PIN para acciones de alto riesgo; no se agregaron permisos
de sistema, intérpretes de shell ni instalaciones automáticas de apps.

### API nueva

Todas estas rutas están bajo `/api/asistente`, con `X-SKY-KEY` y el segundo
factor que ya protege la API:

- `POST /ciclo` — crea plan sin efectos;
- `GET /ciclo/{id}` — consulta estado, sin exponer el texto dictado;
- `POST /ciclo/{id}/siguiente` con `{"aprobado":true}` — aprueba **solo un paso**;
- `POST /ciclo/{id}/verificar` — pide evidencia al agente autorizado;
- `DELETE /ciclo/{id}` — cancela.

El plan es temporal, limitado a seis pasos, expira tras 30 minutos y no se
reanudará tras reiniciar el proceso; no se inventan éxitos después de un fallo.

### Estados reales

| Estado | Significado |
| --- | --- |
| READY | Paso listo; aún no ejecutado |
| RUNNING | El agente está procesando |
| DISPATCHED | Orden enviada/iniciada; efecto **no verificado** |
| WAITING_VERIFICATION | El flujo está detenido hasta obtener evidencia |
| VERIFIED | El agente confirmó la acción |
| FAILED | Falló una acción; el flujo se detiene |
| CANCELLED | El propietario canceló el flujo |

**Limitación:** algunas operaciones, como abrir una URL en el navegador, no
pueden demostrar que la página terminó de cargar. En ellas SKY informa `SENT`,
no `VERIFIED`, y no ejecuta pasos dependientes sin evidencia.

## Instalación en computadora Windows

El mecanismo de inicio de Windows **ya existía** en el proyecto y no se
reemplazó. En el equipo de destino con Python y los requisitos del repositorio:

```powershell
git fetch origin
git switch feat/sky-operational-cycle-mobile-20261023
python -m pip install -r requirements.txt
python agente_dispositivo.py --ver-politica
```

Después, iniciar mediante el lanzador ya existente
`INICIAR_SKY_ASISTENTE_WINDOWS.bat` o el arranque correspondiente del
proyecto. Revisar en Windows los permisos de la política local, instalar
los controladores opcionales de voz y verificar que el agente escuche
solamente en `127.0.0.1:8766`. No activar controles de alto riesgo
por defecto.

Con SKY levantada en el equipo local abrir `http://127.0.0.1:8765/hud`.
En navegadores compatibles puede instalarse también como aplicación de
escritorio mediante la opción de instalación del navegador.

## Instalación en teléfono Android

Se agregó una PWA **real** del HUD existente:

- `/mobile` — entrada al mismo HUD con diseño responsive;
- `/manifest.webmanifest` — metadatos e iconos PNG 192/512;
- `/sky-sw.js` — service worker que **no almacena API, conversaciones,
  credenciales, audio ni HTML privado**;
- `/api/mobile/install-info` — capacidades declaradas sin simulación.

La PWA instalada puede chatear, utilizar la voz que soporte el navegador y
ejecutar acciones a través de la API **del equipo Windows** en el que corre
SKY. No es una APK nativa, ni concede acceso al sistema operativo Android.
Para abrir aplicaciones nativas del propio Android se necesitará un agente
Android separado y los permisos visibles del sistema.

### Conexión entre PC y teléfono

No usar `127.0.0.1` de la PC en el teléfono: cada equipo tiene su propio
localhost. Exponer **solo la API autorizada**, mediante HTTPS privado
(por ejemplo Tailscale Serve con autenticación y controles de acceso) y
abrir esa dirección HTTPS desde Chrome Android. Usar «Añadir a pantalla de
inicio» o «Instalar aplicación» según la versión del navegador.

**No abrir los puertos 8765 ni 8766 de forma pública a Internet.**
La instalación en ambos equipos necesita validar HTTPS, origen seguro,
sesión del propietario, micrófono, audio y permisos antes de usarla a diario.

## Verificación sin computadora física

GitHub Actions ejecuta
`.github/workflows/sky-operational-cycle.yml` para verificar sintaxis
Python/JavaScript, órdenes encadenadas, parada de emergencia, PIN, evidencia,
cancelación, privacidad del service worker y recursos PWA.

Ejecutar localmente:

```powershell
python -m pip install "pytest>=8,<10" "httpx>=0.27,<1" "fastapi>=0.115,<1"
python -m pytest -q tests/test_sky_execution_cycle.py
```

La ejecución CI no certifica micrófono Windows, TTS físico, apertura real
de Word/Excel, conectividad Android ni capacidades de todos los proveedores
externos. Esas validaciones deberán realizarse en los dispositivos
autorizados.

## Objetivo de fiabilidad

No existe un porcentaje 100/100 universal demostrable por agregar código.
Los indicadores deben medir, por cada capacidad concreta: órdenes reconocidas,
pasos verificados, pasos enviados sin evidencia, fallos, latencia, permisos,
errores de voz, estabilidad y completitud en las plataformas realmente probadas.

Esta entrega incrementa trazabilidad y funcionalidad real sin sustituir
SKY CORE, sus modelos, su API, SKY Aula, SKY SENTINEL ni el Skillpack previo.
