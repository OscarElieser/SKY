# SKY Home Server + SKY Mobile — fase inicial verificable (26/10/2026)

**Objetivo aprobado:** una sola SKY. La PC de casa (Windows 11, i3 de generación no confirmada, 8 GB RAM, SSD) será el nodo principal 24/7; el celular Android será un cliente remoto; la PC del trabajo (Windows 10 Pro, i7-12700, 16 GB, SSD) conservará su agente independiente. **Ninguna instalación física se modificó con esta rama.**

## Inventario confirmado en main

- API original: `metaverse/api.py`, autenticación `X-SKY-KEY` y segundo factor si está configurado; agente Windows independiente `127.0.0.1:8766`.
- Cerebro y motores existentes: `neural_core/sky_cerebro.py`, `neural_core/providers.py`, Ollama local y proveedores remotos configurables. No se reemplazan.
- Supervisor: `iniciar_sky_autonomo.py` con `--minimized`, `--status` y `--install-startup`; inicia con **sesión Windows**, no garantiza servicio antes de iniciar sesión.
- Instalador: `instalar_sky.ps1` acepta `-SinOllama`, `-SinVoz` y `-Siempre`. La instalación normal incluye dependencias y descargas considerables: no usarla a ciegas en una PC con 8 GB.
- HUD instalable: `metaverse/mobile_pwa_api.py`, `/mobile` y manifest PWA. **No equivale a una APK nativa.**
- La rama `feature/sky-mobile-agent-android-20261026` ya es ancestro de `main` (comparación GitHub: **0 commits por delante y 338 por detrás** en el momento de la auditoría). No hace falta volver a fusionarla.
- **Sí existe** un Android Agent nativo en Kotlin: `mobile/android-agent`, con emparejamiento temporal, token por dispositivo, lista blanca de apps y confirmación local. Es un agente de apertura de apps, **no un chat móvil completo**; consulta órdenes cada 6 s solo mientras la actividad está visible. No hereda permisos de propietario ni controla el teléfono en segundo plano.
- `templates/sky_design_flutter` es una plantilla de diseños Flutter, no un cliente móvil SKY funcional.

### Línea base de CI de main, comprobada en GitHub Actions

En el commit `ea4207c6a9cf15517756d6c10f2f2944c15f156a` había pruebas exitosas **y fallos reales**:
- `SKY security and global regression` (run 40428484967): **526 pasaron y 1 falló**, `tests/test_sky_v12_6_fiabilidad.py::test_artefactos_de_flutter_en_la_plantilla_no_rompen_los_disenos` (`FileExistsError` en `build/test_cache`).
- `SKY v10.6 global voice and recovery verification` (run 40428484854): fallo de `tests/test_sky_hud_chat_voice_bridge.py::ChatIntentTests::test_actual_browser_hud_parser_accepts_period_and_accents` (el parser de HUD no devolvió `chat` para una frase).
- Estos fallos preexistentes **no se atribuyen a esta rama** ni se consideran resueltos. No fusionar sin atenderlos.

## Qué implementa esta rama (sin alterar el comportamiento anterior)

1. `neural_core/sky_home_routing.py`: selector puro de proveedor. La nube solo se elige con autorización **por solicitud**; los datos privados requieren autorización adicional. `SKY_LOCAL_ONLY` impide la nube. No cambia de proveedor silenciosamente ante errores. Con autorización, prioriza nube para evitar cargar un modelo grande en la PC de 8 GB; sin ella, usa Ollama solo si responde localmente.
2. `metaverse/sky_home_api.py`: rutas `GET /api/sky/home/status` y `POST /api/sky/home/chat`, integradas en la **API propia** mediante `metaverse/api.py`, protegidas por `require_key` (incluido MFA cuando esté activo). El chat es **solo texto** y usa `providers.reply` existente. No ejecuta herramientas, no lee archivos, no envía memorias ni concede derechos al Android Agent.
3. `scripts/sky_home_preflight.py --json`: inspección local **solo lectura** de RAM (Windows), espacio libre, Python, puertos loopback, entorno virtual y presencia de Tailscale; no lee claves ni inicia servicios. Un puerto abierto no demuestra que SKY esté sano.
4. `tests/test_sky_home_routing.py` y `.github/workflows/sky-home-server.yml`: pruebas de privacidad y de no-fallback, sintaxis y preflight en runner CI. El runner **no es la computadora del usuario**.

### Contrato de la nueva API, para pruebas locales del propietario

`GET /api/sky/home/status` exige `X-SKY-KEY` y, cuando corresponda, `X-SKY-SESSION`.

`POST /api/sky/home/chat` acepta este cuerpo de ejemplo **sin datos personales**:

```json
{
  "texto": "Explica qué es un SSD",
  "historial": [],
  "proveedor": "auto",
  "datos": "generales",
  "autorizar_nube": true,
  "autorizar_datos_privados": false
}
```

La clasificación predeterminada es `datos: privados` y `autorizar_nube: false`. El cliente debe mostrar qué datos se compartirán y con qué proveedor antes de marcar la autorización; el servidor **no puede garantizar** que una frase clasificada erróneamente como general no contenga datos privados. Si no hay motor autorizado, responde 409; si el proveedor falla, responde 503 **sin fallback oculto**. No se deben guardar credenciales en el celular ni en URLs.

## Instalación ligera en casa — procedimiento PENDIENTE de autorización y pruebas

1. Hacer respaldo del equipo y de la carpeta `~/.neuralt` de SKY cuando corresponda; nunca subir `.env`, claves, tokens ni bases privadas a GitHub. Comprobar espacio libre y que Windows Update/reinicio no interrumpa el servicio.
2. Instalar Git y Python compatible; clonar SKY en una carpeta propia. No sobrescribir la instalación del trabajo. Verificar la rama y el estado limpio.
3. Ejecutar **solo lectura**: `python scripts/sky_home_preflight.py --json`. Esto no prueba modelos ni micrófono.
4. Para un primer perfil ligero, **después de revisar el instalador y sus dependencias**, considerar `INSTALAR_SKY_WINDOWS.bat -SinOllama -SinVoz -Siempre`. La opción `-Siempre` cambia energía y registra arranque **al iniciar sesión**, no crea un servicio Windows antes del login. El modo sin voz se refiere al motor local; el dictado del móvil depende de sus permisos y compatibilidad.
5. Configurar en el PC (no en GitHub) una clave de proveedor remoto, autenticación fuerte y MFA. Conservar `SKY_LOCAL_ONLY=1` si se necesita privacidad local total; para nube autorizada, dejarlo desactivado y aprobar cada solicitud. Añadir respaldo local pequeño **solo después de medir RAM real**, no descargar modelos 7B por defecto.
6. Probar `/api/health`, `/api/health/listo`, `/api/sky/home/status` autenticado y `/api/sky/home/chat` con texto no sensible. Medir RAM, latencia, CPU y consumo en reposo/carga; verificar recuperación tras reinicio y caída de internet.

### Acceso privado desde Android

- Instalar Tailscale en casa y en el celular, con la misma red privada y controles de acceso. Usar **Tailscale Serve**, no Funnel ni redirección de puertos del router. La documentación oficial recomienda `tailscale serve --bg 8765` para compartir un servicio local con HTTPS **dentro de la tailnet**: https://tailscale.com/docs/reference/tailscale-cli/serve
- El servidor FastAPI debe seguir escuchando en `127.0.0.1:8765`, el agente Windows en `127.0.0.1:8766`. **No abrir 8765/8766 a internet.** Comprobar `tailscale serve status`, HTTPS, nombre de host permitido, MFA y políticas del servidor antes de usarlo fuera de casa.
- Tailscale protege la conexión, **pero no reemplaza** autenticación SKY, permisos por dispositivo ni controles contra sesiones robadas.
- No usar `tailscale funnel` para la API privada; Funnel la haría accesible públicamente.
- Para disponibilidad real 24/7 se necesitan corriente, red, reinicio automático controlado, copias de seguridad y supervisión. No habilitar inicio de sesión automático de Windows solo para arrancar SKY: debilita la seguridad del equipo.

## App Android: alcance y siguiente implementación

La PWA es una opción temporal para probar HUD; el Android Agent Kotlin **ya existe**, pero no es el cliente de conversación solicitado. La app definitiva debe reutilizar la API y su seguridad, sin copiar `SKY_API_KEY` al teléfono.

Contrato a desarrollar y revisar antes de exponer chat móvil:
- Sesiones **de alcance limitado** emitidas tras aprobación del propietario + MFA, ligadas a un dispositivo, revocables y con expiración; scopes separados `chat:write`, `chat:read`, `status:read` y `device:request`. No reutilizar el token de cola Android como si fuera clave maestra.
- Pantallas: emparejamiento, chat voz/texto, estado del servidor, historial permitido, autorizaciones por tarea, errores/reconexión. No prometer escucha permanente en segundo plano sin permisos y pruebas de Android.
- Backend: API de chat con consentimiento por turno, sin herramientas de control automático; acciones en dispositivos solo con política del agente correspondiente y evidencia. Cifrado en tránsito y almacenamiento seguro de token en Android Keystore.
- Verificación: compilación Android CI, instalación en teléfono, cambio Wi-Fi/datos, servidor apagado, token revocado, permisos denegados, caducidad, pérdida de red, consumo de batería y pruebas de voz.
- El cliente Flutter puede construirse posteriormente; **no confundir** la plantilla `sky_design_flutter` con una app lista.

## Criterios para integrar en main

- CI nuevo en verde y revisión de cambios.
- Pruebas API autenticadas, con y sin MFA; autorización de nube, datos privados y error de proveedor; ninguna llamada externa no consentida.
- Resolver o aislar formalmente los dos fallos de CI de main anteriores; sin ocultarlos.
- Validación de RAM/voz/Windows en equipos físicos y prueba de HTTPS/Tailscale + Android antes de declarar disponibilidad real.
- Revisión de seguridad del servidor y del futuro token móvil; sin puertos públicos, sin contraseñas en repositorio.
- Integración gradual con HUD y app; el endpoint nuevo no cambia por defecto las rutas actuales del asistente.

**Estado:** rama de desarrollo, no desplegada, no fusionada a `main`. Las pruebas automáticas no certifican 24/7, teléfono ni Windows reales.
