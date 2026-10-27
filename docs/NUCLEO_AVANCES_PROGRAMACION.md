# SKY — Aprendizaje de avances oficiales de programación

## Integración implementada

La rama main incorpora neural_core/sky_programming_learning.py, un sistema aditivo que complementa sky_web_learning.py. Consulta datos públicos de **releases y etiquetas estables oficiales** de GitHub, los archiva en una base SQLite local y los ofrece al cerebro como REFERENCIAS. No sustituye al modelo local, ni a la API propia, ni a los sistemas de programación, voz, documentación, seguridad o memoria de SKY.

### Cobertura inicial (18 proyectos)

Python (python/cpython), Node.js (nodejs/node), TypeScript (microsoft/TypeScript), Flutter (flutter/flutter), Dart (dart-lang/sdk), React (facebook/react), Next.js (vercel/next.js), Angular (angular/angular), Vue (vuejs/core), Rust (rust-lang/rust), Go (golang/go), Kotlin (JetBrains/kotlin), FastAPI (fastapi/fastapi), Django (django/django), Supabase (supabase/supabase), Prisma (prisma/prisma), PyTorch (pytorch/pytorch) y Vite (vitejs/vite).

Este es un catálogo de repositorios de confianza *declarados*, no una garantía de que todos tengan un release estable reciente o de que su API siempre responda. Si no existe un release actual o es demasiado antiguo, SKY consulta etiquetas estables del repositorio. La fecha de una etiqueta corresponde al commit asociado: **NO equivale a una fecha de lanzamiento oficial**. Se descartan borradores y prereleases.

### Funcionamiento autónomo

- El worker existente del aprendizaje web de SKY corre cuando la API está activa. Espera una hora tras el inicio; ejecuta el lector de noticias web existente y, a continuación, el nuevo lector de releases.
- Hasta 4 repositorios oficiales por ciclo, no más de una consulta por repositorio cada 24 horas. Los 18 se reparten de forma equitativa entre ciclos.
- Solo se aceptan URLs con dominio github.com y ruta oficial del repositorio autorizado. Se utiliza api.github.com/repos/OWNER/REPO/releases/latest y, para versiones faltantes o antiguas, las rutas oficiales de tags y commit correspondientes al repositorio autorizado.
- Conserva versión, título, fecha, URL y hasta dos resúmenes de cambios publicados en releases. En etiquetas usa la fecha del commit y marca el origen como etiqueta; no afirma haber leído notas de lanzamiento. Nunca ejecuta fragmentos. Al cerebro se le pasan **versiones, tipo de referencia y enlaces**, no textos ejecutables.
- Evita duplicados, guarda hasta 500 registros, elimina automáticamente metadatos antiguos tras 180 días y conserva los existentes si la red falla.
- No manda preguntas del usuario, documentos, contraseñas, claves ni PIN a GitHub. No utiliza credenciales de GitHub para estas consultas públicas.

### Configuración local (.env)

Las opciones por defecto son:

    SKY_INTERNET=1
    SKY_WEB_LEARNING=1
    SKY_PROGRAMMING_LEARNING=1

Es opcional escoger una lista limitada al catálogo permitido:

    SKY_PROGRAMMING_REPOS=python/cpython;microsoft/TypeScript;flutter/flutter;vercel/next.js

El comportamiento es reversible con SKY_PROGRAMMING_LEARNING=0. Si SKY_LOCAL_ONLY=1 o SKY_INTERNET=0 o SKY_WEB_LEARNING=0, se deshabilita toda conexión de este lector. No es necesario un GitHub Token; las peticiones públicas siguen sujetas a los límites de la API de GitHub.

### Comprobación desde Windows PowerShell

    git status --short
    git pull --ff-only origin main
    & .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_sky_programming_learning.py" -v
    & .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_sky_web_learning.py" -v
    & .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_sky_core_learning.py" -v
    & .\.venv\Scripts\python.exe -c "from neural_core.sky_programming_learning import sync; print(sync())"
    & .\.venv\Scripts\python.exe -c "from neural_core.sky_programming_learning import status,describe; print(status()); print(describe())"

A las preguntas del asistente también responde:
- «SKY, actualiza avances de programación».
- «SKY, últimos avances de programación».

### Precauciones

Las pruebas automatizadas simulan datos: comprueban formatos, caducidad, retención, procedencia, límites, privacidad y comandos de voz. No garantizan disponibilidad real de la red del equipo. La existencia de una nueva versión **no prueba compatibilidad ni calidad**; comparar APIs, migraciones y pruebas del proyecto antes de actualizar. El módulo **no reentrena** pesos neuronales ni efectúa instalaciones, descargas, despliegues o alteraciones del repositorio.

Para profundizar después: fuentes adicionales oficiales (lenguajes/IDEs/BD), revisión verificable de notas de versión y clasificación de breaking changes, pruebas de compatibilidad contra los proyectos de SKY y conjunto LoRA supervisado con rollback.
