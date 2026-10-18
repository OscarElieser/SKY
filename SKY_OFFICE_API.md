# SKY Office Studio API — v8.0

Servidor: `http://127.0.0.1:8765` (predeterminado local).

El token maestro se crea en `local_data/sky_api_token.txt` y debe presentarse
mediante cabecera `X-SKY-KEY`. No poner el token en URLs, código público ni capturas.

## Consultar formatos

`GET /api/office/formats` requiere `X-SKY-KEY`.

## Crear un archivo real

`POST /api/office/generate` requiere `X-SKY-KEY` y `Content-Type: application/json`.

```json
{
  "kind": "pptx",
  "title": "Mi presentación educativa",
  "prompt": "Tema: innovación y aprendizaje",
  "content": "# Introducción\n- Idea 1\n- Idea 2\n# Actividades\n- Taller en equipo",
  "csv": "",
  "template": "general",
  "ai_provider": "none"
}
```

**Respuesta:** los bytes reales del formato solicitado, su MIME y
`Content-Disposition: attachment; filename=...` para guardarlo.

Formatos: `docx`, `pptx`, `xlsx`, `pdf`, `csv`, `md`, `html`.

Para Excel, se puede usar `headers`/`rows` o `csv`:

```json
{
 "kind":"xlsx",
 "title":"Mis ingresos",
 "headers":["Concepto","Monto"],
 "rows":[["Cursos",200],["Servicios",400]],
 "template":"general"
}
```

Plantilla de presupuesto con fórmulas editables:

```json
{"kind":"xlsx", "title":"Presupuesto", "template":"presupuesto"}
```

**IA optativa:** cambiar `ai_provider` a `gemini`, `openai`, `anthropic`,
`ollama`, `mistral`, `groq` o `deepseek` e incluir `prompt`. Solo se envía el
contenido cuando se selecciona un proveedor. Es necesario configurar la API
privada correspondiente o tener Ollama local.

Límites actuales por solicitud: 50.000 caracteres de contenido,
40 columnas, 300 filas (hasta 26 columnas para XLSX con motor interno).
No ejecuta macros ni fórmulas inyectadas por CSV. Las plantillas usan fórmulas
creadas por código, no por entrada libre del usuario.

## Alcance

Este módulo genera y exporta archivos. No reemplaza Word, Excel ni PowerPoint
como editores completos; se abren esos formatos con sus programas compatibles.
Tampoco gestiona aún permisos documentales por cuenta social ni sincronización en la nube.
