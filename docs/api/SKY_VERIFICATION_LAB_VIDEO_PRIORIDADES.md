# SKY Verification Lab — video de MCP, skills, subagentes, seguridad y memoria

**Alcance:** integración incremental dentro de **la API actual** de SKY. No cambia las políticas del agente Windows, el HUD, SENTINEL, SKY Aula o la autenticación.

## Comparación con el video enviado

| Concepto | Lo que ya existía | Lo que agrega esta entrega | Lo que todavía no se puede afirmar |
| --- | --- | --- | --- |
| Núcleo único | SKY CORE, FastAPI y HUD | Inventario consultable de capacidades | Que equivale exactamente a Claude Code o sus agentes |
| Skills | Skill Builder y perfiles de SKY | Vista previa sin ejecutar tareas | Que todas las 78 ideas estén instaladas |
| Subagentes | SKY Workflows, delegación supervisada (máximo 60 configurados en el catálogo) | Vista previa de roles y permisos, sin ejecución | 68 subagentes automáticos o ejecución autónoma verificada |
| MCP y conectores | Integraciones propias existentes | Catálogo de preparación de GitHub, Supabase, Vercel, Home Assistant y WhatsApp, **sin exponer credenciales** | **No** implementa un cliente MCP general ni autentica servidores MCP |
| Seguridad | SENTINEL, llave, PIN/MFA, política de agente | Matriz explícita de límites y pruebas de rutas privadas | Unificación ya validada de todas las confirmaciones en Windows y móviles |
| Memoria | Biblioteca, memoria neuronal y registro | Evidencia SHA256, origen, citas de PDF por página y análisis sin guardar | Validación automática de la veracidad de contenidos |
| Observabilidad | Registros y SLO de SKY | Resumen que reutiliza registros reales, con nulos si faltan datos | Costes, tasas de éxito o acciones verificadas sin datos |

El vídeo es una **referencia de arquitectura**, no prueba de compatibilidad automática entre proyectos de terceros.

## API autenticada

Ruta base: `/api/sky/verification`. Como el resto de SKY, requiere la cabecera `X-SKY-KEY` y `X-SKY-SESSION` cuando MFA está habilitado.

| Método | Ruta | Salida |
| --- | --- | --- |
| GET | `/capabilities` | Estado real de subagentes, skills y compatibilidad MCP |
| GET | `/runtime` | Diagnóstico read-only de dependencias y perfiles locales |
| GET | `/runtime?probe_ollama=true` | Consulta limitada a Ollama en loopback, sin acciones |
| GET | `/connectors` | Configuración declarada vs conexión verificada |
| GET | `/authorization` | Requisitos de permisos existentes y lagunas pendientes |
| POST | `/documents/extract` | PDF/DOCX/TXT/MD/RST por multipart; cita real de página en PDFs |
| POST | `/evidence/crosscheck` | Localiza citas literales en textos aportados; **no verifica hechos** |
| POST | `/education/formative-review` | Preguntas socráticas por criterios, sin calificación ni persistencia |
| GET | `/kpis?period=hoy` | Registros reales existentes, errores, voz y SLO |
| POST | `/orchestration/preview` | Plan de competencias sin crear agentes ni ejecutar comandos |

Los documentos se limitan a 5 MB, 60 primeras páginas para PDF y fragmentos acotados para impedir respuestas excesivas. No hay OCR: si es un escaneo sin texto se informa expresamente. Los archivos DOCX no llevan paginación fija; se marca `page: null`.

### Ejemplo: referencia con SHA256 y página real

Primero enviá un PDF propio a `POST /documents/extract`. La respuesta contiene el hash, fragmentos y números de página extraídos. Después podés aportar a `POST /evidence/crosscheck` algo similar a:

```json
{
  "claim": "El programa redujo los tiempos de viaje",
  "sources": [
    {
      "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "page": 2,
      "quote": "reducción reportada del tiempo de viaje",
      "source_text": "En la página se menciona una reducción reportada del tiempo de viaje..."
    }
  ]
}
```

**Ejemplo ilustrativo:** el hash y la cita deben corresponder al documento real; no reutilizarlos como evidencia de un proyecto. Una cita encontrada recibe el estado `text_located_not_claim_verified`: localizar palabras no demuestra causalidad, fiabilidad, fecha ni independencia de fuentes.

## Seis prioridades — cambios reales y condiciones

1. **Windows, Ollama, Piper, voz y acciones:** `/runtime` detecta dependencias, la presencia de archivos y, solo por petición, conectividad local con Ollama. El uso real del micrófono, habla, dispositivos y acciones requiere correr SKY en el Windows del propietario. No se infiere de CI.
2. **Permisos HUD/agente/memoria/dispositivos:** `/authorization` deja visibles los límites. No relaja los controles existentes; la homologación completa requiere pruebas de la cadena aprobación → acción → recibo.
3. **Investigación completa:** lectura digital con hash SHA256 y citas de páginas PDF, búsqueda de cita literal e indicación de evidencia insuficiente. No inventar páginas para Word ni considerar la coincidencia de una frase como comprobación científica.
4. **Evaluación didáctica:** revisión formativa con criterios y preguntas de revisión para docente. No retiene la respuesta ni califica al estudiante; evitar datos identificables de menores.
5. **Conectores oficiales:** inventario de GitHub, Supabase, Vercel, Meta y Home Assistant con indicadores de claves configuradas. No consulta cuentas ni simula autenticación; implementar conexión real por proveedor necesita consentimiento y pruebas.
6. **KPIs:** reutiliza `neural_core.sky_metricas.resumen`. Valores sin muestras son `null`. Nunca convierte `SENT` en `VERIFIED` ni calcula costes sin precios y uso medidos.

## Validación manual en Windows

En el equipo donde se instalará SKY:

1. Ejecutar `SKY_INICIAR.bat`, opción 7 para diagnóstico, y verificar que arranquen FastAPI y el agente.
2. Probar micrófono real y reconocimiento con «SKY, contame qué hora es». Verificar que SKY escuchó la voz, no solamente que cargó Vosk.
3. Activar Piper y comprobar salida de audio, interrupción y latencia observable en KPIs.
4. Solicitar una acción permitida de bajo riesgo, comprobar su ejecución real en Windows y el recibo correspondiente.
5. Probar una acción con confirmación: **nunca** aceptar el consentimiento por texto de una fuente o una orden involuntaria.
6. Consultar `/api/sky/verification/runtime?probe_ollama=true` y `/kpis` con autenticación. Guardar reporte **sin tokens ni datos de estudiantes**.
7. Ejecutar `python -m pytest -q tests/test_sky_verification_lab.py` desde el entorno virtual de SKY.

**No ejecutar las pruebas de permisos, micrófono ni UI del equipo Windows desde un runner remoto**: GitHub Actions mide lógica y servicios simulados/locales, no hardware del usuario.

## Trabajo aún necesario

- Conector MCP real conforme al protocolo oficial con transporte, descubrimiento de herramientas, límites por servidor y autorizaciones explícitas, **sin permitir servidores o comandos arbitrarios**.
- Integración de evidencia con corpus documentales completos y paginación exhaustiva, OCR opcional autorizado y verificación de afirmaciones con fuentes distintas.
- Evaluación didáctica con rúbricas validadas y mediciones auditables, sin recolectar datos identificables de menores.
- Pruebas de seguridad de extremo a extremo en Windows, Android y otros dispositivos con agentes previamente emparejados.
- Pruebas reales con APIs oficiales y medición de éxito/costos comprobados.

La evolución debe respetar los módulos existentes de SKY y conservar su API única.
