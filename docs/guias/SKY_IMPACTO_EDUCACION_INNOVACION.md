# SKY Impacto — implementación inicial (octubre 2026)

Integrado como extensión de **la API y los modelos existentes de SKY**, sin sustituir sus módulos de escritorio, voz, telemetría, memoria, deportes ni documentos.

## Funciones reales de esta entrega

- Planificador de investigación para ensayos, monografías, tesis, protocolos, informes y diagnósticos. Devuelve estructura, preguntas y fuentes sugeridas, **sin afirmar haber investigado**.
- Plan de clases de seis etapas, desde educación inicial hasta posgrado/doctorado, con tiempo distribuido, objetivo y guion de interacción. `lesson/step` devuelve una consigna para el siguiente turno de voz o texto, **no evalúa automáticamente el conocimiento de los estudiantes**.
- Estructurador de proyectos para competencias (problema, Canvas preliminar, entregables, pitch, validación). Todos los supuestos no verificados quedan explícitos.
- Simulador matemático de jurado cuando el usuario aporta la rúbrica y las puntuaciones. **No sustituye la evaluación oficial ni garantiza premios**.
- Auditoría de metadatos bibliográficos: informa campos incompletos, sin simular que verificó DOI, autores o referencias en internet.
- Catálogo de fuentes públicas y universitarias para consultas **HTTPS de solo lectura, limitadas a dominios conocidos y ejecutadas únicamente por solicitud expresa**. Una fuente registrada no es una API conectada ni acceso a una red gubernamental interna.
- Instrucciones añadidas a los flujos de texto (`neural_core.assistant`) y voz (`sky_cerebro` y `sky_asistente_personal`) para atender peticiones educativas e innovadoras con el modelo configurado, sin reemplazar la síntesis de voz ni el reconocedor existentes.
- Telemetría agrupada como «Educación e Innovación», reutilizando la medición real de solicitudes de SKY.

## API existente: rutas añadidas

Las rutas se montan bajo `/api/impacto` con `Depends(require_key)` del sistema principal, incluida la verificación de segundo factor si está habilitada.

| Método | Ruta | Resultado |
|---|---|---|
| GET | `/status` | Capacidades y estado declarado |
| GET | `/sources?category=educacion` | Catálogo de fuentes |
| POST | `/sources/{source_id}/consult` | Descarga limitada de fuente precargada, cuando se solicita |
| POST | `/research/plan` | Plan metodológico, fuentes por consultar |
| POST | `/lesson/plan` | Plan de clase con etapas |
| POST | `/lesson/step` | Instrucción para un turno interactivo |
| POST | `/innovation/project` | Propuesta inicial y Canvas por validar |
| POST | `/competition/review` | Puntuación calculada desde rúbrica aportada |
| POST | `/references/audit` | Inspección de metadatos bibliográficos |

Ejemplos usando la llave habitual de SKY:

```bash
curl -sS -H "X-SKY-KEY: $SKY_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"topic":"Los números hasta 20","level":"inicial","minutes":35}' \
  http://127.0.0.1:8765/api/impacto/lesson/plan

curl -sS -H "X-SKY-KEY: $SKY_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"challenge":"Reducir residuos urbanos","competition":"Hackathon Nicaragua"}' \
  http://127.0.0.1:8765/api/impacto/innovation/project

curl -sS -H "X-SKY-KEY: $SKY_API_KEY" \
  -X POST http://127.0.0.1:8765/api/impacto/sources/marena/consult
```

Si está activo el segundo factor, añadir también `X-SKY-SESSION` como en las demás rutas privadas.

## Fuentes estratégicas

Se incluyen MINED, INATEC, INTUR, MARENA, MIFIC, BCN, INIDE, plan nacional de lucha contra la pobreza 2022–2026, estrategia nacional de educación 2024–2026, Hackathon Nicaragua, Rally Nacional, Nicaragua Diseña, UNESCO, UIS, ONU, UNdata, Banco Mundial, CEPAL, OMS, FAO, Parlamento Europeo, MIT, Harvard y Stanford, entre otras.

**Vigencia:** para octubre de 2026, la estrategia educativa 2027–2030 es una *propuesta en estudio*, no debe atribuirse vigencia sin nueva verificación. El marco 2024–2026 y el plan nacional 2022–2026 también requieren revisar la versión vigente antes de cada trabajo.

La consulta del sitio principal sólo recupera extractos de texto. No lee automáticamente PDF, informes completos, artículos cerrados, bases privadas o rúbricas. Para un proyecto científico o concurso, SKY debe utilizar documentos originales autorizados y confirmar las fechas antes de realizar afirmaciones.

## Pruebas

```bash
python -m pip install pytest fastapi httpx
PYTHONPATH=. pytest -q tests/test_sky_impacto.py
```

Existe el flujo independiente `.github/workflows/sky-impacto-tests.yml`, que compila los módulos y ejecuta pruebas sin acceso a internet ni credenciales.

## Limitaciones y próximas fases

1. RAG documental con descarga verificada de PDFs oficiales, versionado, citas por página y evidencia recuperada. No mezclar un índice de fuentes con investigación ya realizada.
2. Orquestación de clase verdaderamente interactiva: micrófono, reproducción TTS, turnos, seguimiento de progreso, autorizaciones de docentes y protección de datos de menores.
3. Extensión de generación documental con la capacidad Office ya presente en SKY (DOCX, PDF, presentaciones y hojas de cálculo).
4. Obtención de bases vigentes y rúbricas oficiales para competencias; probar prototipos y evaluar con evidencia real.
5. Evaluaciones reproducibles, pruebas integrales en Windows y dispositivos móviles y análisis de calidad pedagógica.
6. Ampliar conectores sólo con APIs públicas documentadas y/o credenciales expresamente autorizadas, sin acceso no autorizado a redes gubernamentales.

**Nada de lo anterior debe presentarse como implementado antes de superar pruebas y demostrar ejecución real en el equipo destino.**
