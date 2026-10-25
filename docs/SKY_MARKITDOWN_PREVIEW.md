# SKY Knowledge — Vista previa de MarkItDown (opcional)

## Qué hace realmente
Añade a la **API actual** de SKY una conversión a Markdown para PDF, DOCX, PPTX y XLSX usando Microsoft MarkItDown 0.1.9. Reutiliza la autenticación del propietario y se mantiene **desactivada por defecto**.

- No cambia los lectores de `sky_multimodal_reader.py`.
- No modifica la memoria cifrada ni el esquema de datos.
- No indexa, entrena, ejecuta instrucciones del documento, descarga modelos o publica nada.
- Devuelve Markdown, límite de tamaño y estado de truncamiento; no garantiza OCR ni exactitud semántica.
- Se realiza una conversión en proceso hijo con entrada en memoria, límites de tamaño y tiempo, limpieza de credenciales del entorno, plugins desactivados y bloqueo de conexiones TCP de Python en el worker.

**Limitación de seguridad importante:** un proceso hijo no es una sandbox de sistema operativo. MarkItDown puede hacer I/O con los permisos del usuario del proceso. Para contenido ajeno/no confiable se recomienda añadir un contenedor/VM aislada, sin red ni acceso a archivos privados, antes de habilitar el uso general. No exponer la API a Internet ni permitir cargas arbitrarias.

## Instalación voluntaria

En el entorno virtual dedicado de SKY, revisar las dependencias y ejecutar solo cuando el propietario decida:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements_markitdown_optional.txt
```

Configurar solo en el entorno local:

```powershell
$env:SKY_MARKITDOWN_ENABLED="1"
```

La configuración de SKY existente (llave y segundo factor cuando aplique) sigue siendo obligatoria.

## API

- `GET /api/sky/knowledge/capabilities` presenta `markitdown_preview.enabled`, `installed`, formatos y límites.
- `POST /api/sky/knowledge/convert-markdown-preview`: `multipart/form-data`, campos `file` y `approved=true` explícito.

Los archivos permitidos son `.pdf`, `.docx`, `.pptx`, `.xlsx`, hasta 4 MB. El Markdown tiene máximo 60 000 caracteres. Si no hay texto extraído, la respuesta refleja `content_extracted=false`. La conversión no inserta contenido automáticamente en la biblioteca existente; el propietario deberá usar el flujo independiente de indexación con consentimiento si lo requiere.

## Aceptación

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_sky_markitdown_optional.py
```

El CI optativo instala el paquete en su entorno desechable y convierte un DOCX auténtico. El éxito del CI **no** significa que el paquete esté instalado en el Windows propietario ni que se hayan probado documentos de clientes de cualquier origen.

## Evolución RAG

Primero comparar calidad de recuperación del índice cifrado actual con alternativas; no sustituir `sky_knowledge_library.py` por LlamaIndex/Haystack hasta comprobar aislamiento de datos, métricas, control de costes y citas. El siguiente incremento debe usar un índice paralelo opcional, no migrar automáticamente documentos privados.

Fuente: https://github.com/microsoft/markitdown y https://pypi.org/project/markitdown/0.1.9/
