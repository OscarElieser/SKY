# SKY IA — Auditoría de ejecución real y continuidad (26-10-2026)

## Alcance y honestidad de la verificación

El propietario autoriza revisar el HUD `http://127.0.0.1:8765/` y solicita que SKY pueda realizar realmente lo trabajado. Ese host es **localhost de su Windows**, inaccesible desde el entorno remoto de auditoría. No se ha navegado, hecho clic, escuchado audio ni ejecutado una operación física en su PC desde GitHub. La evidencia disponible comprende el código del repositorio y las salidas de PowerShell compartidas por el propietario.

**Importante:** código presente ≠ servicio en línea ≠ acción despachada ≠ acción físicamente verificada. SKY no debe confirmar tareas sin evidencia del resultado.

## Hallazgos con evidencia

| Área | Evidencia | Conclusión |
|---|---|---|
| API/latencia | Diagnóstico físico: `/api/health` p95 3,3 ms, `hud.js` p95 15,4 ms, saludo p95 97,4 ms; sin errores HTTP | **Velocidad de salud, HUD y saludo comprobada**; no equivale a respuesta rápida para toda petición de IA |
| Vosk | Modelo local existe; inicio manual alcanzó `escucha natural activada` | Servicio puede arrancar; **captura/acciones continuas no certificadas** |
| Instancias | Cuatro procesos que coinciden con `sky_manos_libres.py` en el listado de Python | Podrían ser padre/hijo del entorno Windows; falta ParentProcessId y exclusión de micrófono verificada |
| HUD chat | Se transcribió `Abrir panel de conversación.` pero no se abrió ventana; después se aplicó parche y se ejecutaron cinco pruebas locales correctamente | Parser corregido; **apertura visual final pendiente** |
| Agente Windows | `--status`: API y agente en línea; capacidades reportadas: status, open_url, launch_app, media_control, media_key, volume, play_media, notify, task_action | **No** incluía `open_file` ni `type_text`; no inferir que puede escribir en Word |
| Word/Office | `sky_office.create_document` genera DOCX real; `sky_e2e_pc_real.py` puede probar abrir Word y generar archivo con consentimiento | Motor de archivo real presente; encadenar petición, redacción, guardado, apertura y verificación **no completado** |
| Secuencias | `sky_execution_cycle.is_sequence` exige conectores como `y luego` | `Abrí Word y redactá un informe` no entra en esa regla y necesita un planificador propio |
| Docencia | Academy, evaluación y multimedia tienen rutas y módulos | Hay código y pruebas; la clase de extremo a extremo no está certificada en aula real |
| Investigación | Conectores y verificador existen; el chequeo Crossref optativo valida metadatos | No prueba acceso lícito al texto completo ni cada afirmación/cita |
| Teléfono | Módulos API y marcadores móviles; plataformas reales exigen permisos/cuenta del dueño | No afirmar llamada/SMS realizados sin callback o comprobante |
| Programación/skills | Catálogos, herramientas, IDE y conectores presentes | No equivale a compilación de todos los lenguajes ni integraciones activas |
| Android | PWA/API y elementos multiplataforma | No demuestra agente móvil nativo instalado ni controles de SIM/Android |
| Seguridad | SENTINEL, políticas, niveles de riesgo y confirmaciones | Conservarlos: no convertir autorización general en desactivación de seguridad |

## Riesgos que afectan la experiencia

1. **RAM:** última medición física 94,8 % ocupada; `llama-server` usaba ~4,2 GB. Cambios de voz y UI no arreglan por sí solos la presión de memoria.
2. **Procesos múltiples:** abrir manualmente Vosk y además arrancar SKY completo puede generar procesos que compiten; validar mutex del listener único en Windows y revisar ParentProcessId.
3. **Permisos:** perfil multimedia admite abrir apps, pero no editar texto ni abrir documentos arbitrarios. Para `type_text` se requiere habilitación explícita y confirmación según política local.
4. **Flujos no conectados:** muchas pantallas y catálogos no equivalen a un agente que complete acciones compuestas. El plan de tarea debe conservar estado, verificar efectos y comunicar errores.
5. **Ramas:** PR #52 no debe fusionarse a `main` si existen conflictos, CI fallido o validación física pendiente; preservar otras contribuciones y PR #51 de STT.

## Comprobación integral de solo lectura en Windows

Con SKY iniciado, en otra consola:

```powershell
Set-Location "C:\Users\PC 1\Documents\Desktop\SKY"
& .\.venv\Scripts\python.exe .\scripts\sky_runtime_full_audit.py --save
& .\.venv\Scripts\python.exe .\iniciar_sky_autonomo.py --status
```

La auditoría reutiliza `sky_integral_operational_check.py`, la política de capacidades, el motor Office ya existente y las rutas de SKY. Verifica generación DOCX **en memoria** y no abre aplicaciones. Guarda un informe sin datos de contacto, conversaciones, claves ni contenido de documentos.

## Prueba física optativa, **con consentimiento presencial**

```powershell
& .\.venv\Scripts\python.exe .\scripts\sky_e2e_pc_real.py --confirm --app word --open-document
```

Esa orden **sí abre Word** y guarda un DOCX de prueba en `Documentos/SKY_E2E`; solo ejecutarla cuando la persona esté frente al PC, quiera realizar la prueba y haya habilitado los permisos del agente. El resultado debe marcar `physically_verified` y `overall_pass` para tratarlo como exitoso. No ejecutar automáticamente desde una auditoría de solo lectura.

## Aceptación mínima antes de `main`

- Una única instancia efectiva de Vosk, sin doble escucha ni reintentos en bucle.
- Decir `Abrí panel de conversación` abre efectivamente la ventana del HUD.
- Orden para Word genera y abre un archivo DOCX real, correctamente nombrado y comprobado, sin transgredir políticas.
- Voz, escritura, botones multimedia y control de ventanas funcionan en equipo físico.
- Tareas de docencia, investigación y creación muestran salida real y fuentes/archivos verificables.
- La API conserva la latencia lograda, los KPIs, el historial y la protección SENTINEL.
- La PR está libre de conflictos y todas las suites exigidas terminan correctamente.

**No afirmar 100 % de SKY hasta disponer de evidencias de cada módulo, dependencia externa y dispositivo.**
