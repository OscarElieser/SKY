# SKY IA Universal v10.1 — Guía de uso e instalación

**Visión del proyecto:** Oscar Elieser Chamorro Guzmán.

## Preparación

1. Extrae el ZIP en una carpeta nueva; no sobrescribas v10.0.
2. Instala Python 3.11 o 3.12, FFmpeg/FFprobe y dependencias `pip install -r requirements.txt -r requirements_studio.txt`.
3. Guarda `.env` y `local_data` anteriores con SKY apagado antes de migrar. Nunca publiques claves, tokens, SQLite personales ni imágenes privadas en GitHub.
4. Arranca `INICIAR_SKY_V9_WINDOWS.bat` o `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765`.
5. Entra a `http://127.0.0.1:8765/sky`. Los controles avanzados permanecen dentro de **Espacios → Estudio creativo**. BAQUEANO continúa solo para el propietario autorizado.

## Idiomas

- Cambia el idioma desde el selector pequeño 🌐. El idioma elegido se conserva en ese navegador. La preferencia del creador también puede guardarse mediante API autenticada.
- Hay un catálogo de 31 lenguas y etiquetas regionales. Las **11 frases esenciales** disponen de traducción offline en 10 idiomas. Otras cadenas del interfaz todavía permanecen en español. Los idiomas adicionales pueden ser ampliados con nuevos catálogos.
- Para traducción libre usa `POST /api/i18n/translate` con `provider=gemini` (o `ollama`) y `consent=true`. Esta opción requiere un proveedor funcionando y compartir explícitamente el texto solicitado. SKY no envía memoria privada junto al texto en esa API.
- Dictado depende del navegador y de su motor de reconocimiento; algunos idiomas no estarán disponibles.

## Máscaras y pistas globales

En Studio, crea un proyecto de video, importa el video o la fotografía y agrega una pista visual con una imagen desde la biblioteca. En el apartado plegable **Pistas globales y máscaras animadas**, especifica intervalo y opcionalmente las máscaras como JSON de tiempos (segundos) e identificadores de archivos de máscara. La animación interpola la opacidad espacial entre máscaras y se puede mover por fotogramas clave. Guarda, manda a render y previsualiza **el resultado renderizado**, no solo una simulación.

Restricciones: 8 pistas globales, 2 con máscara animada; máscara animada hasta 30 s por pista, 8 posiciones y 512 px de ancho de máscara; FFmpeg y memoria disponibles necesarios.

## Worker separado (recomendado)

En el proceso API configura `SKY_CREATIVE_WORKER=0`, y en otra consola ejecuta `python sky_render_worker.py` o su lanzador. Para el modo local simplificado, conserva el worker embebido predeterminado y **no inicies simultáneamente otro worker**. Los renders pendientes no se pierden al reiniciar la API; los interrumpidos necesitan revisión manual.

## Seguridad antes de producción

- API local por defecto, protegida mediante clave larga `X-SKY-KEY`. Evita publicarla en una red abierta.
- Define `SKY_TRUSTED_HOSTS=localhost,127.0.0.1,testserver,tu-dominio.com` al publicar detrás de proxy con TLS, y configura proxies de confianza explícitos.
- CSP, headers, no-store, throttling básico en proceso, límite de JSON, aislamiento de renders y errores de Gemini neutros implementados.
- **Bloqueadores de despliegue:** MFA, cuentas creador con roles verificables y rotación, limitación distribuida contra abuso, WAF, secretos centralizados, rate limits por ruta, colas Redis/Postgres para escala, backup cifrado/restauración probada, sandbox para FFmpeg y auditoría de terceros.
- Usa una cuenta/clave diferente para BAQUEANO; no expongas `service_role` Supabase.

## Pruebas

```bash
PYTHONPATH=. pytest -q
node --check metaverse/static/creative.js
node --check metaverse/static/sky-home.js
node --check metaverse/static/sky-language-ui.js
```

En pruebas locales v10.1 pasaron **191** (185 anteriores + 6 nuevas), y el render externo entregó un MP4 verdadero. La prueba Chromium fue bloqueada por el entorno, por lo que no está certificada la experiencia completa en navegador.

## Autenticación de Gemini

Establece la clave `GEMINI_API_KEY` solamente en tu `.env` privado y utiliza «Probar conexión real Gemini» desde Creative Studio. No se ejecuta automáticamente. La validación real no fue posible sin credencial; no subas esta clave a GitHub ni al ZIP.
