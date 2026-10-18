# SKY IA Universal v9.0 · Experience Orchestrator

**Visión y concepción:** Oscar Elieser Chamorro Guzmán.
**Objetivo:** hacer de SKY un asistente personal multimodal, creativo y multidisciplinario
que coordine resultados reales sin perder el metaverso, la comunidad, la API ni Office Studio.

## Estado verificable

**Versión integrada en el código**, no solo documento ni prompt:

1. **33 roles de asistencia** para reconocer la necesidad del usuario (educación,
   economía, finanzas, programación, investigación, audiovisual, 3D, salud informativa,
   viajes, BAQUEANO y más). SKY puede combinar hasta 5 enfoques por consulta.
2. **SKY Workbench**: planificación, tareas persistidas, aprobación y ejecución de
   herramientas locales en dos fases. No hay comandos de sistema arbitrarios.
3. **SKY Visual Creator**: convierte una descripción en una página HTML/CSS
   responsive editable, ofrece preview y guarda la especificación JSON.
4. **SKY Neural Core**: mapa de módulos e indicadores de solicitudes reales a SKY API.
   No pretende leer el pensamiento oculto de los modelos.
5. **Office Studio integrado**: genera archivos DOCX, PPTX, XLSX, PDF, CSV,
   Markdown y HTML con datos reales; los archivos aprobados quedan disponibles
   para descarga con la clave privada.
6. **Metaverse Engine y Social Universe** conservados (salas, chat multiusuario,
   avatares geométricos, memoria de usuarios, mundos proceduralmente generados).
7. **Memoria personal local, bitácora y respaldo** para notas y proyectos nuevos.
8. **Gemini, OpenAI, Anthropic, Mistral, DeepSeek, Groq y Ollama** opcionales,
   requieren claves o instalación propias. La selección del proveedor es explícita.
9. Se conservan NeuralT MLP+GRU, SKY Studio 3D 2.5D, dispositivos voluntariamente
   emparejados y las utilidades autorizadas de BAQUEANO.

## Iniciar

**Windows:** instalar Python 3.11 o 3.12, extraer el ZIP, ejecutar
`INICIAR_SKY_V9_WINDOWS.bat`, y abrir `http://127.0.0.1:8765/studio`.

**Linux / macOS:**

```bash
bash iniciar_sky_v9_linux_mac.sh
```

Una clave aleatoria se genera la primera vez en `local_data/sky_api_token.txt`.
No publiques esa clave. El programa arranca **solo en tu computadora**.

El menú principal del nuevo panel conecta:

- `/studio` → SKY Experience Orchestrator y Neural Core.
- `/` → mundos 3D y edición.
- `/community` → comunidad y social.
- `/office` → documentos.
- `/docs` → API privada.

El panel Streamlit heredado, con finanzas, IA, visión y dispositivos, se inicia por
separado desde `INICIAR_WINDOWS.bat`, instalando `requirements.txt`.

## Probarlo

- Escribí **«Creá una academia virtual de turismo con un laboratorio 3D»**.
- Pulsá **Analizar y planificar**: aparecen las especialidades y las etapas.
- Pulsá **Generar vista previa**: SKY genera una página HTML de verdad, editable.
- Elegí **Guardar diseño visual**, prepará la tarea y pulsá **Confirmar**.
- Para una presentación, seleccioná **Archivo Office**, elegí PPTX y pegá
  contenido auténtico en el editor; confirmá y descargá.
- Para un mundo, seleccioná **Crear mundo** y luego abrí el metaverso.
- Consultá **SKY Neural Core** para comprobar los eventos reales del API.

## Desarrollo y pruebas

```bash
python -m pip install -r requirements_studio.txt
python -m pip install pytest httpx
python -m pytest -q
```

**Importante:** el proyecto es una base local integrada, no un producto global terminado.
No hay pruebas de disponibilidad continua, simulación inmersiva AAA, GPU/neural engine
propio para video fotorrealista, administración pública comercial ni registro oficial
completado. Se necesita despliegue, revisión de seguridad y pruebas de hardware.

Para documentación técnica: [`SKY_V9_API.md`](SKY_V9_API.md).
Para SKY v8 y anteriores, consultar [`README.md`](README.md).
Para autoría y expediente previo, revisar los archivos `AUTORIA_*` y el PDF incluido.

**No se ha modificado BAQUEANO, no se han publicado cambios en una web y no se han ejecutado transacciones.**
