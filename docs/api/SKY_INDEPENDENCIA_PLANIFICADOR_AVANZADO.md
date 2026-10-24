# SKY IA — Arquitectura propia y planificador avanzado local
**Repositorio:** `OscarElieser/SKY`. **Estado:** desarrollo en rama; no implica despliegue ni instalación de todas las herramientas.

## Regla central

**SKY es la única asistente visible.** Conversación, decisión de tareas, memoria, seguridad, coordinación, registro y API son de SKY. Los proveedores de modelos son motores intercambiables y los subagentes son trabajadores internos limitados por permisos. Ninguna herramienta de terceros puede asumir la identidad, las credenciales maestras o el control administrativo de SKY.

**Independencia realista:** sin obligación de usar servicios de OpenAI, Anthropic, Google, Microsoft, Canva ni Gamma. Podemos ejecutar modelos de *pesos abiertos* con licencias compatibles localmente. Esto **no** equivale a reproducir los modelos propietarios de esas empresas ni a tener gratuitamente sus servicios, infraestructura, datasets o funciones exclusivas.

## Lo implementado en la rama

- `neural_core/sky_advanced_planner.py`: razonamiento **local opcional** con Ollama o llama.cpp, salida estructurada JSON, validación estricta de tareas, máximos de respuesta/tiempo y *fallback* al plan determinista si falla el modelo.
- `neural_core/sky_supervisor.py`: combina planificación, roles de SKY, motor de workflows persistente, aprobación individual y agregación de resultados.
- `neural_core/sky_capability_inventory.py`: detecta herramientas locales disponibles sin instalar nada, sin ejecutarlas y sin conceder privilegios.
- API original ampliada:
  - `GET /api/sky/supervisor/catalogue`: incluye diagnóstico del planificador;
  - `POST /api/sky/supervisor/analyze` y `/prepare`: aceptan `planner_mode: "advanced" | "deterministic"` (predeterminado avanzado);
  - `GET /api/sky/capabilities/local`: herramientas detectadas **no equivale a Skill funcional**;
  - `GET /api/sky/supervisor/jobs/{workflow_id}`: estados y evidencias.
- `tests/test_sky_advanced_planner.py`: LLM malicioso, prohibición de escalar permisos o cambiar parámetros, rutas de loopback, redundancia de solicitudes, motor llama.cpp simulado, fallback local y detección de herramientas.
- Pruebas Linux y Windows integradas en GitHub Actions.

### Invariantes de seguridad del planificador

1. El planificador recibe la **solicitud breve**, no el contenido completo de documentos ni los secretos.
2. **Solo contacta el servidor de modelo local en loopback** por defecto; ninguna llamada a servicios de nube, redirecciones HTTP ni otros hosts.
3. Su respuesta solo puede **reordenar roles ya habilitados** y describir objetivos/verificaciones; no modifica el contenido ni los parámetros de ejecución.
4. Cualquier referencia a un paso inexistente, nueva acción, duplicado o formato inválido hace descartar el plan del modelo.
5. No puede saltarse bloqueos: fuentes no verificadas, contenido faltante, compras, terminal, publicaciones y borrados se retienen hasta disponer de una Skill específica.
6. `SKY Workflows` necesita aprobación del dueño antes de empezar una tarea con efectos. La evidencia de los pasos se registra después; preparar NO es ejecutar.
7. La idempotencia usa el hash de la solicitud y del material recibido, no la salida variable del modelo, para evitar trabajos duplicados.

## Configuración en Windows (PowerShell)

### Opción A: Ollama local (integración ya existente en SKY)

Instalar Ollama según su documentación oficial y **descargar voluntariamente un modelo compatible**, revisando sus condiciones de licencia antes de redistribuir/comercializar.

```powershell
ollama list
ollama pull qwen2.5:7b
$env:SKY_PLANNER_BACKEND = 'ollama'
$env:SKY_PLANNER_LOCAL_URL = 'http://127.0.0.1:11434'
$env:SKY_PLANNER_LOCAL_MODEL = 'qwen2.5:7b'
$env:SKY_ADVANCED_PLANNER = 'auto'
```

Se recomienda utilizar los modelos instalados reales: `ollama list` muestra el inventario local; `SKY_PLANNER_LOCAL_MODEL` puede coincidir con `OLLAMA_MODEL`. Los comandos anteriores **no se ejecutan automáticamente**. No compartir el puerto de Ollama a internet.

### Opción B: llama.cpp (sin Ollama)

Iniciar llama.cpp server usando un GGUF obtenido legalmente, revisar memoria/VRAM y verificar el puerto. Ejemplo conceptual: `llama-server -m <modelo-local.gguf> --host 127.0.0.1 --port 8080`; los nombres de binarios/opciones pueden variar con la versión instalada.

```powershell
$env:SKY_PLANNER_BACKEND = 'llamacpp'
$env:SKY_PLANNER_LLAMACPP_URL = 'http://127.0.0.1:8080'
$env:SKY_PLANNER_LLAMACPP_MODEL = 'local-model'
$env:SKY_ADVANCED_PLANNER = 'auto'
```

llama.cpp ofrece endpoints compatibles con solicitudes de chat y salida restringida JSON. Un modelo seleccionado debe admitir bien el formato, idioma español y contexto requerido; no todos los modelos sirven para planificación.

### Modo seguro, sin modelo instalado

```powershell
$env:SKY_ADVANCED_PLANNER = 'off'
```

SKY sigue atendiendo mediante el planificador determinista, sin bloquear el resto de su API. Para comprobar el resultado se usa `GET /api/sky/supervisor/catalogue` con la autenticación de propietario.

## Qué herramientas autorizar para aspirar a una SKY integral

**Herramientas de sistema, no servicios obligatorios de otras empresas:**

| Dominio | Opciones locales | Qué faltará validar antes de decir “funciona” |
|---|---|---|
| Razonamiento conversacional | Ollama, llama.cpp + modelos de pesos abiertos | Calidad, licencia, VRAM/RAM, latencia, idioma, pruebas |
| Voz sin servicios remotos | whisper.cpp, Vosk, faster-whisper, Piper u otro TTS local autorizado | Micrófonos, permisos, latencia, idioma, interrupciones, consentimientos |
| Memoria y búsqueda | SQLite/PostgreSQL local, embeddings locales, FAISS u otros índices | Privacidad, procedencia, borrado, cifrado y segmentación |
| Programación | Python, Node, Git, GitHub opcional, sandboxes de pruebas | Ejecución segura, repos propios, ramas/PR, tests reales |
| Word/Excel/PowerPoint/PDF | LibreOffice, python-docx, openpyxl, python-pptx, pypdf | Fidelidad de formatos, plantillas, previsualización, fuentes |
| Diseño gráfico | SVG/HTML/CSS, Inkscape, Krita, GIMP, motores de difusión locales compatibles | Edición real, consistencia visual, compatibilidad y licencias de modelos |
| Imagen generativa | ComfyUI con modelos de licencia compatible | GPU/VRAM, workflow, seguridad de nodos y calidad |
| Video/audio | FFmpeg, editores y modelos locales opcionales | GPU, tiempos, formatos, subtítulos y derechos |
| 3D | Blender, motores GLB/Three.js locales | Salida editable, calidad y pruebas |
| Navegador y PC | Playwright y agente SKY de Windows bajo mínimos privilegios | Dominios permitidos, permisos, confirmación y evidencia |
| Hogar | Home Assistant local | Equipos compatibles, emparejamiento y privacidad |
| Organización | SKY Scheduler y Workflows ya existentes | Reanudación tras reinicio, alertas y políticas de ejecución |

**No confundir “instalado/detectado” con “skill integrada”:** antes de declarar una capacidad terminada hacen falta ejecutor real, contrato de entrada/salida, permisos, verificación, pruebas y desactivación.

La GPU, RAM, espacio en disco y potencia eléctrica condicionarán las capacidades locales. Sin conocer el hardware del equipo no se debe prometer multimodalidad avanzada simultánea ni un modelo de tamaño específico.

## Evolución de funcionalidades inspiradas en otras IA

- **ChatGPT / Claude / Gemini:** razonamiento, multimodalidad, búsqueda y recuperación de archivos, herramientas y análisis; implementar los flujos propios de SKY con modelos/índices locales y pruebas.
- **Copilot:** trabajo en repositorios con agentes de programación, refactor, generación de tests y revisión bajo PR; no ejecutar comandos arbitrarios desde prompts.
- **Gamma / Canva:** generadores de presentaciones, diseños, brand kits, plantillas y edición con herramientas propias; no imitar o redistribuir su código/activos privados.
- **Suno y otros generadores musicales:** composición, letra, MIDI, mezcla y generación de audio mediante motores locales licenciados. No prometer acceso a modelos/API propietarios sin permiso.
- **Adobe:** edición de fotos/videos/PDF y efectos mediante herramientas instaladas propias o interfaces documentadas; sin suponer acceso a Photoshop o Firefly.

**Todas las capacidades citadas son objetivos**, no funcionalidades implantadas automáticamente en esta PR. El catálogo detallado de Skills ya está en `docs/api/SKY_CATALOGO_78_SKILLS_2026.md`.

## Próximas etapas técnicas

1. **Cerrar confiabilidad y seguridad del núcleo:** CI verde + pruebas físicas del agente Windows, autorizaciones, voz, restauración.
2. **Mejorar planificación:** comparación de modelos locales, evaluador independiente de calidad, programación de dependencias tipo DAG y límites de CPU/GPU, RAM/tokens.
3. **Integrar investigación verificada local y web autorizada:** indexador RAG con citas y frescura; no fingir búsqueda abriendo un navegador.
4. **Ampliar creación:** Office completo y edición visual con archivos de salida revisables; imágenes/videos/voz mediante motores compatibles y benchmarks.
5. **Skill Manager robusto:** registros firmados, catálogo real, permisos por Skill, pruebas e instalación aprobada por el propietario.
6. **Operación continua:** arranque opcional del servicio, health checks y restablecimiento controlado en cada dispositivo; “activo todo el tiempo” solo mientras hay equipo/energía/servicio funcionando.
7. **Aprendizaje supervisado:** memorias corregibles, evaluaciones, resultados comparables y propuestas de mejoras que pasan por revisión; nunca modificar el motor de políticas unilateralmente.

## Prueba mínima

En la rama, con SKY autenticada:
1. Abrir `/flows` → SKY Agent Supervisor.
2. Escribir «Creá una presentación y diseñá una interfaz sobre este contenido».
3. Aportar el contenido real en la casilla de referencia.
4. Analizar, revisar `planner_backend` y el orden sugerido; si no hay modelo, debería indicar `deterministic`.
5. Preparar el flujo y aprobarlo específicamente.
6. Ver resultados y artefactos reales desde `/api/sky/supervisor/jobs/{id}`.

**No fusionar ni desplegar sin CI del último commit y ensayo Windows de extremo a extremo.**
