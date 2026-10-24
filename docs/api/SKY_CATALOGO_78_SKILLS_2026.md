# SKY — Portafolio de Skills integrables (plan técnico, 2026)
**Estado:** catálogo propuesto; NO significa que las Skills estén instaladas ni funcionando.
**Regla:** conservar la API existente de SKY, SKY CORE, el agente de dispositivo, memoria, UI holográfica y políticas locales; ampliar mediante adaptadores.

## Contrato mínimo de una Skill
Cada Skill necesita: `id`, `name`, `version`, `description`, `owner`, `input_schema`, `output_schema`, `required_permissions`, `risk_level`, `provider_adapters`, `timeout`, `cost_budget`, `capability_probe`, `smoke_test`, `dry_run`, `verification`, `rollback` y `auditing_policy`.
Estados verificables: `proposed`, `scaffolded`, `implemented`, `tested`, `enabled`, `blocked`. Nunca reportar `enabled` sin prueba y permisos reales.

Seguridad: mínimo privilegio por Skill; herramientas con tokens delegados; autorizaciones de un solo uso para cambios externos; red y archivos limitados por propósito; `prompt injection` tratada como datos; secrets en vault del sistema; auditoría sin copiar contenidos privados; aprobación de usuario para pagos, envíos, borrados, cambios de permisos e instalaciones.

## Catálogo propuesto (78 ideas, no funcionalidad declarada)

### A. Vida cotidiana e identidad (12)
| ID | Skill | Valor | Prioridad |
|---|---|---|---|
| SKY-001 | personal-daily-brief | Agenda, pendientes, clima y resúmenes autorizados | P0 |
| SKY-002 | personal-goals | Objetivos, planes, progreso y recordatorios | P1 |
| SKY-003 | personal-memory | Memoria corregible con fuente, consentimiento y expiración | P0 |
| SKY-004 | personal-preferences | Preferencias explícitas por contexto y dispositivo | P0 |
| SKY-005 | personal-tasks | Captura, priorización, delegación y seguimiento | P0 |
| SKY-006 | personal-habits | Hábitos y metas de bienestar no clínicas | P2 |
| SKY-007 | personal-notifications | Alertas discrecionales configurables | P0 |
| SKY-008 | personal-contacts | Directorio y relaciones de contactos autorizados | P1 |
| SKY-009 | personal-family-planner | Organización familiar con separación de permisos | P2 |
| SKY-010 | personal-errands | Compras, diligencias y recorridos con consentimiento | P2 |
| SKY-011 | personal-accessibility | Dictado, lectura de pantalla, subtitulado y accesibilidad | P1 |
| SKY-012 | personal-emergency-assist | Contactos y protocolos de emergencia configurables | P2 |

### B. Trabajo y documentos (12)
| ID | Skill | Valor | Prioridad |
|---|---|---|---|
| SKY-013 | office-docx | Redactar, revisar y editar documentos Word | P0 |
| SKY-014 | office-xlsx | Crear hojas, fórmulas, análisis y gráficos auditables | P0 |
| SKY-015 | office-pptx | Presentaciones y conferencias con plantillas | P0 |
| SKY-016 | office-pdf | Leer, crear, combinar, firmar con herramientas autorizadas | P1 |
| SKY-017 | office-ocr | Leer escaneos cuando no exista texto accesible | P2 |
| SKY-018 | office-email | Buscar, redactar, clasificar y enviar con confirmación | P0 |
| SKY-019 | office-calendar | Crear, comparar horarios y administrar reuniones | P0 |
| SKY-020 | office-meeting | Transcribir reuniones consentidas, acuerdos y seguimiento | P1 |
| SKY-021 | office-drive | Gestionar archivos en proveedores conectados | P1 |
| SKY-022 | office-contract-review | Resumir cláusulas, señalar riesgos; no sustituye abogado | P2 |
| SKY-023 | office-forms | Formularios y encuestas con revisión antes del envío | P1 |
| SKY-024 | office-knowledgebase | Búsqueda RAG en documentos conectados y archivos locales | P0 |

### C. Investigación, educación e idiomas (10)
| ID | Skill | Valor | Prioridad |
|---|---|---|---|
| SKY-025 | research-web | Búsqueda global actual y fuentes citadas | P0 |
| SKY-026 | research-crosscheck | Contrastar afirmaciones y fechas entre fuentes | P0 |
| SKY-027 | research-academic | Papers, bibliografía, síntesis y límites de evidencia | P1 |
| SKY-028 | education-lesson | Planes pedagógicos diferenciados por nivel | P1 |
| SKY-029 | education-assessment | Rúbricas, pruebas, ejercicios y retroalimentación | P1 |
| SKY-030 | education-tutor | Tutor de ciencias, humanidades y formación técnica | P1 |
| SKY-031 | education-apa | Referencias APA verificadas, nunca fuentes inventadas | P1 |
| SKY-032 | language-translate | Traducción contextual y terminología por idioma | P1 |
| SKY-033 | language-speaking | Conversación, corrección y ejercicios de pronunciación | P1 |
| SKY-034 | research-data-analysis | Análisis estadístico, tablas, gráficos y reproducibilidad | P1 |

### D. Ingeniería de software y tecnología (12)
| ID | Skill | Valor | Prioridad |
|---|---|---|---|
| SKY-035 | dev-repo-audit | Revisar arquitectura, deuda técnica y riesgos | P0 |
| SKY-036 | dev-code | Modificar código con tests y revisiones | P0 |
| SKY-037 | dev-debug | Reproducir errores, diagnosticar y probar correcciones | P0 |
| SKY-038 | dev-github | Commits, branches, PR, checks y CI | P0 |
| SKY-039 | dev-testing | Pruebas unitarias, integración, E2E y regresión | P0 |
| SKY-040 | dev-database | SQL, PostgreSQL, Supabase, consultas autorizadas | P1 |
| SKY-041 | dev-deployment | Deploys revisados, rollback y métricas | P1 |
| SKY-042 | dev-api-builder | Contratos OpenAPI, SDK, versionado y seguridad | P0 |
| SKY-043 | dev-ui-ux | Prototipos y mejoras accesibles de interfaz | P1 |
| SKY-044 | dev-mobile | Flutter, Android y herramientas iOS compatibles | P1 |
| SKY-045 | dev-security-audit | Análisis defensivos en repos propios/autorizados | P0 |
| SKY-046 | dev-documentation | Manuales, ADR, documentación y changelogs | P1 |

### E. Creatividad, diseño y multimedia (10)
| ID | Skill | Valor | Prioridad |
|---|---|---|---|
| SKY-047 | creative-design | Banners, flyers, brochures, brand kits y redes | P1 |
| SKY-048 | creative-slides | Adaptadores Gamma / Canva / PowerPoint con permisos | P1 |
| SKY-049 | creative-image | Generación/edición de imagen con proveedor autorizado | P1 |
| SKY-050 | creative-video | Edición FFmpeg, guiones, subtítulos, clips | P1 |
| SKY-051 | creative-voice | TTS, locución, STT multilingüe y privacidad | P0 |
| SKY-052 | creative-music | Letras, melodías y composición con APIs autorizadas | P2 |
| SKY-053 | creative-podcast | Podcast, voces, limpieza y publicación supervisada | P2 |
| SKY-054 | creative-animation | Motion design 2D/3D y efectos | P2 |
| SKY-055 | creative-3d | Blender, GLB, escenas y prototipos 3D | P2 |
| SKY-056 | creative-brand-strategy | Identidad visual y consistencia de campañas | P1 |

### F. Negocios y finanzas (10)
| ID | Skill | Valor | Prioridad |
|---|---|---|---|
| SKY-057 | business-marketing | Estrategias, campañas, segmentos y calendarios | P1 |
| SKY-058 | business-social | Planificar publicaciones y responder con autorización | P1 |
| SKY-059 | business-crm | Seguimiento de clientes/aliados y consentimiento | P2 |
| SKY-060 | business-sales | Cotizaciones, propuestas y seguimiento comercial | P2 |
| SKY-061 | business-finance | Presupuestos, gastos y reportes contables | P1 |
| SKY-062 | business-inventory | Inventario y alertas de existencia | P2 |
| SKY-063 | business-analytics | KPIs, embudos, conversión y reportes | P1 |
| SKY-064 | business-hr | Formatos, perfiles y cronogramas de personal | P2 |
| SKY-065 | business-operations | SOP, procesos y gestión de proyectos | P1 |
| SKY-066 | business-baqueano | Asistencia al proyecto BAQUEANO sin desplegar ni publicar sin aprobación | P1 |

### G. Turismo, hogar, salud y entretenimiento (12)
| ID | Skill | Valor | Prioridad |
|---|---|---|---|
| SKY-067 | travel-research | Destinos, fuentes oficiales, temporadas y riesgos | P1 |
| SKY-068 | travel-planner | Itinerarios, rutas y presupuestos comprobables | P1 |
| SKY-069 | travel-navigation | Mapas y navegación legal dentro de dispositivos | P2 |
| SKY-070 | home-assistant | Control autorizado de luces, escenas y dispositivos | P1 |
| SKY-071 | shopping-comparison | Precios actuales, especificaciones y comercios | P2 |
| SKY-072 | food-recipes | Recetas y menús por ingredientes y preferencias | P2 |
| SKY-073 | wellness-coach | Rutinas generales de bienestar; sin diagnósticos | P2 |
| SKY-074 | health-record-organizer | Organizar información sanitaria con consentimiento explícito | P3 |
| SKY-075 | sports-football | Resultados, estadísticas, Real Madrid y calendarios | P1 |
| SKY-076 | sports-predictions | Proyecciones probabilísticas explicables, no garantías | P2 |
| SKY-077 | entertainment-control | Música, videos y controles multimedia reales | P0 |
| SKY-078 | device-orchestrator | Agentes de Windows/macOS/Linux/móvil con permisos por dispositivo | P0 |

## Adaptadores, NO imitaciones de productos
- Razonamiento/herramientas: OpenAI, Google Gemini, Anthropic Claude, Groq, DeepSeek, Mistral, Ollama; configurar sólo APIs disponibles y autorizadas.
- Documentos: Microsoft Graph, Google Workspace, LibreOffice local, Python Office libraries.
- Diseño y creatividad: Canva, Gamma, Adobe Firefly, generación de imágenes, FFmpeg, Blender.
- Música y voz: proveedores con APIs oficiales contractualmente disponibles, motores STT/TTS locales.
- Ingeniería: GitHub, MCP, Playwright, Python, testing, Docker, entornos aislados.
- Actividad doméstica: Home Assistant.
- Flujo de automatización: programador local y opcional n8n/otros motores.
- Seguridad: SKY SENTINEL / políticas del agente, aprobaciones de un solo uso, logs y KPIs reales.

**No asumir acceso a APIs privadas porque exista una suscripción de consumidor** (ej. ChatGPT, Copilot, Canva, Suno); comprobar elegibilidad, costos, TOS y scopes antes de instalar.

## Orden recomendado
1. **P0 — Fiabilidad y ayuda real:** cerrar SKY API v12.1, control de Windows y medios, voz, memoria, calendario, correo, Office, investigación, depuración, tests, verificación y seguridad.
2. **P1 — Productividad amplia:** agentes en Google/Microsoft, documentos avanzados, programación, educación, marketing, multimedia y análisis.
3. **P2 — Creatividad y vida cotidiana:** música, video avanzado, viajes, compras, hogar, 3D y deporte.
4. **P3 — Alto grado de sensibilidad:** registros de salud, finanzas conectadas y otras cuentas delicadas con consentimiento granular y auditoría.

## Puerta de calidad antes de activar cualquier Skill
1. ¿Existe una herramienta ejecutora real y versionada? 2. ¿API/token/permisos disponibles?
3. ¿Está limitada al recurso y operación necesarios? 4. ¿Tiene pruebas negativas?
5. ¿Hace `dry-run` y pide confirmación en acciones externas? 6. ¿Entrega evidencia de ejecución?
7. ¿Registra resultados sin datos privados? 8. ¿Puede desactivarse y revertirse?
Si alguna respuesta falla: reportar `proposed` o `blocked`; **no venderlo como instalado**.
