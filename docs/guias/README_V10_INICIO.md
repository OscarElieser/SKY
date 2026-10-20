# SKY IA v10.0 — Instalación y pruebas

## Requisitos

- Python 3.11 o 3.12 (recomendado)
- FFmpeg y FFprobe en PATH
- Dependencias: `pip install -r requirements.txt -r requirements_studio.txt`
- Para seguimiento local: `opencv-python-headless` y NumPy (declarados en requirements)
- Para Gemini real: una clave `GEMINI_API_KEY` configurada **localmente**, nunca subida a GitHub ni incluida en el ZIP

## Inicio

1. Descomprime SKY IA v10.0 en una carpeta nueva.
2. Conserva respaldos previos antes de copiar `local_data` o `.env` de versiones anteriores.
3. En Windows ejecuta `INICIAR_SKY_V9_WINDOWS.bat` (el nombre del iniciador se mantiene por compatibilidad).
4. Entra a `http://127.0.0.1:8765/sky`, selecciona Espacios → Creative Studio.
5. Accede usando la clave maestra local. Los usuarios sociales no reciben acceso al estudio ni a BAQUEANO.

## Editar un video

1. Importa un video MP4 y una imagen PNG para superponerla.
2. Crea un proyecto de video o abre uno existente.
3. En **Seguimiento de objetos y capas de video** señala clip, imagen de capa, X/Y y tamaño.
4. Para seguir una región, utiliza **Seguir objeto**. SKY devuelve puntos editables y registra muestras perdidas.
5. Guarda la versión nueva, renderiza MP4 y luego selecciona **Vista previa** para extraer el fotograma preciso del render actual.
6. Exporta el proyecto `.skyzip` para continuar la edición en otra instalación.

## Gemini

En Creative Studio, pulsa **Probar conexión real Gemini (opcional)** después de configurar `GEMINI_API_KEY`. Esta acción hace una llamada de texto real, puede consumir cuota y requiere Internet. No se ejecuta al iniciar SKY. Si no hay clave muestra un error explícito. No se deben colocar claves en archivos públicos.

## Validar

`PYTHONPATH=. pytest -q`

## Seguridad

No uses `--host 0.0.0.0` ni expongas SKY a Internet sin autenticación fuerte, TLS, límites de petición y auditoría de aplicaciones. Mantén las credenciales fuera del repositorio y nunca permitas que una sesión social use la clave del creador.
