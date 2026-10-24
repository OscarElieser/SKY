# SKY GLOBAL — despliegue verificable, idiomas, inclusión y gobernanza

Esta incorporación **no reemplaza** SKY CORE, FastAPI, SENTINEL, su agente Windows, voz,
Office, Aula, diseño, memoria, proyectos ni los flujos existentes. La nueva
comprobación se integra en el botón **DIAG** y reutiliza la autenticación del
propietario de SKY.

## Funciones que ya pueden ejecutarse

1. `GET /api/sky/global/readiness` responde con un informe privado y `Cache-Control: no-store`.
2. Reutiliza el control de arranque `metaverse/deployment_v102.py` (no crea reglas
   de seguridad paralelas).
3. Comprueba **conexión real a Redis** usando `PING`, no solo la presencia de la URL.
4. Mide etiquetas estáticas **realmente revisadas** para en, pt, fr, ar, zh, ja y sw;
   no confunde catálogo de idiomas con traducción integral.
5. El HUD central carga el traductor de etiquetas aprobado que ya utilizaban otras
   páginas, sin enviar chats ni archivos a proveedores.
6. El HUD contiene enlace para saltar a la conversación con teclado, avisos de estado
   y conversación anunciables, foco visible y respeto a `prefers-reduced-motion`.
7. El mismo DIAG muestra fallos medidos y límites sin inventar que una auditoría
   jurídica, un despliegue internacional o una prueba de lector de pantalla ocurrió.

## Ejecución local

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_sky_global_readiness.py
.\.venv\Scripts\python.exe -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
```

Abrí el HUD, autenticá al propietario y elegí **DIAG**. El informe global también
puede consultarse desde PowerShell:

```powershell
$headers = @{ "X-SKY-KEY" = $env:SKY_API_KEY }
# Agregar X-SKY-SESSION cuando el MFA del dueño está habilitado.
Invoke-RestMethod "http://127.0.0.1:8765/api/sky/global/readiness" -Headers $headers
```

Si la clave se creó en un archivo privado de SKY, usá esa clave sin imprimirla,
reenviarla a chats ni incorporarla a scripts versionados.

## Estados e interpretación

- `pass`: comprobación **medida en ese equipo** con un criterio limitado.
- `fail`: función no preparada, no disponible o por debajo del umbral.
- `unverified`: hace falta prueba del servicio exterior, usuarios reales,
  personal evaluador o autoridad competente.

La bandera `SKY_BEHIND_TLS_PROXY=1` **no** equivale a TLS validado desde Internet.
Tampoco lo equivale establecer `SKY_DEPLOYMENT_MODE=public`. La comprobación
`global_ready` solo podrá ser `true` cuando *todas* las pruebas reales, incluidas
las externas, estén respaldadas; no existen opciones para marcar certificaciones
a partir de variables de entorno.

## Dependencias para un lanzamiento mundial real

| Requisito | Evidencia para desbloquear |
| --- | --- |
| Internet mundial | Entornos distribuidos operativos, dominio, TLS probado, balanceo, certificados, métricas por región |
| Escalado | Pruebas sostenidas de concurrencia y límites del motor IA y sus proveedores |
| Recuperación | Copias cifradas probadas mediante restauraciones completas, RTO/RPO y failover |
| Idiomas | Etiquetas revisadas + evaluación real de conversación, voz, acentos, traducción y culturas |
| Seguridad | Pentesting autorizado, rotación de secretos, revisión dependencias, cifrado y respuesta ante incidentes |
| Regulación | Avisos, base jurídica, derechos, retención, transferencias internacionales, evaluaciones de impacto y auditoría independiente |
| Inclusión | WCAG 2.2, teclado, lectores de pantalla, contraste y pruebas con usuarios reales |
| Costos | Control por cuenta/servicio, cuotas reales, presupuestos y alertas de disponibilidad |

Los servicios con costos, tokens o cuentas externas **no se contrataron ni activaron**
automáticamente. Nunca incluir claves en GitHub. Los controles de seguridad siguen
bloqueando los usos no autorizados.

## Archivos

- `neural_core/sky_global_readiness.py` — verificaciones sin efectos secundarios.
- `metaverse/global_readiness_api.py` — router privado, montado en la API actual.
- `metaverse/api.py` — integración mínima con el router.
- `metaverse/static/hud.html`, `hud.css` y `hud.js` — mejoras funcionales.
- `tests/test_sky_global_readiness.py` — regresiones de autenticación, fallos y accesibilidad.
- `.github/workflows/sky-global-readiness.yml` — comprobación CI de los cambios.

**Límite esencial:** este cambio implementa comprobaciones técnicas y mejoras
accesibles utilizables, **no** despliega centros de datos, compra servicios,
reemplaza una auditoría profesional ni certifica el sistema.
