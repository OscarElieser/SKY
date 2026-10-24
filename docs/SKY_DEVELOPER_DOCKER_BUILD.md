# SKY Developer — Compilación y pruebas REALES (Docker local)

Se integra en la API y HUD existentes. Este módulo NO sustituye SKY CORE, Docencia, SENTINEL ni los demás módulos.

## Condiciones previas

1. Tener Docker Engine / Docker Desktop con contenedores Linux instalado y funcionando. **Para código no confiable, preferir Docker rootless, un equipo o VM desechable y mantener Docker actualizado**. Los contenedores no son una frontera de seguridad absoluta; Docker Desktop/daemon con privilegios elevados no elimina el riesgo de fuga al anfitrión.
2. Configurar en SKY un PIN propietario y autenticación X-SKY-KEY (+ MFA si está activa). Nunca pegar ese PIN en GitHub.
3. Descargar voluntariamente las imágenes compiladoras. Durante el uso del ejecutor no se descargan imágenes y se bloquea la red del contenedor.
4. Activar dos variables en el entorno de SKY, exclusivamente después de revisar el riesgo:
    SKY_CODE_RUNNER_ENABLED=1
    SKY_CODE_RUNNER_CONTAINER_ACK=1
5. Reiniciar la API o servicio local para aplicar las variables. Cada solicitud de ejecución exige consentimiento y PIN de SKY; ninguna orden del LLM puede omitirlo.

## Imágenes aceptadas

| Lenguaje | Imagen Docker previa | Archivo principal |
|---|---|---|
| Python | python:3.12-alpine | main.py |
| JavaScript | node:22-alpine | main.js |
| TypeScript | sky-typescript:5.7.3 | main.ts |
| C | gcc:14-bookworm | main.c |
| C++ | gcc:14-bookworm | main.cpp |
| Go | golang:1.24-alpine | main.go |
| Rust | rust:1.85-slim | main.rs |
| Java | eclipse-temurin:21-jdk | Main.java |
| PHP | php:8.3-cli-alpine | main.php |
| Ruby | ruby:3.3-alpine | main.rb |
| Bash | bash:5.2 | main.sh |

**Los 53 lenguajes/formalismos del catálogo SKY no se declaran compilados**: estos 11 son perfiles de ejecución disponibles cuando su imagen está realmente instalada. TypeScript exige una imagen personalizada construida explícitamente.

Comandos de instalación voluntaria en PowerShell:

~~~powershell
docker pull python:3.12-alpine
docker pull node:22-alpine
docker pull gcc:14-bookworm
docker pull golang:1.24-alpine
docker pull rust:1.85-slim
docker pull eclipse-temurin:21-jdk
docker pull php:8.3-cli-alpine
docker pull ruby:3.3-alpine
docker pull bash:5.2
docker build -t sky-typescript:5.7.3 docker/sky-typescript
~~~

Las etiquetas de imágenes pueden cambiar con el tiempo. SKY consulta el ID sha256 de la imagen predescargada antes de usarla y lo guarda en el resultado de la ejecución. Para entornos de alta seguridad, auditar y fijar los digests de las imágenes en el sistema propietario.

## Uso desde SKY

Abrir HUD → Programación, elegir un lenguaje, introducir el código, agregar opcionalmente pruebas Python unittest o JavaScript node:test, especificar salida esperada, confirmar y proporcionar el PIN. Una solicitud no puede instalar dependencias ni utilizar red.

También reutiliza la API autenticada SKY:

GET /api/developer/build/capabilities
POST /api/developer/build/execute

Ejemplo de cuerpo JSON (se transmite bajo la sesión autenticada y exige PIN):

~~~json
{"language":"Python","files":{"main.py":"print(6 * 7)\n"},"expected_stdout":"42","approved":true,"timeout_seconds":15}
~~~

Las respuestas distinguen la etapa COMPILE de RUN y TESTS; muestran código de salida, tiempo, stdout/stderr acotado, truncamiento y fallos. Un código con error de compilación termina con compile_failed y nunca se informa como ejecutado correctamente. Una salida no coincidente o prueba fallida no se declara éxito.

## Aislamiento aplicado y límites

- Contenedores efímeros y procesos Docker solo en el entorno propietario; nunca se ejecutan compiladores de usuario directamente en el sistema anfitrión.
- Docker --network none, --pull never, --read-only, --cap-drop ALL, --security-opt no-new-privileges, --pids-limit 64, --cpus 1, --memory 768m, --user 65534:65534.
- Carpeta de trabajo efímera (tmpfs), sin montaje de carpetas privadas, sin Docker socket dentro del contenedor, sin variables de secretos del anfitrión, sin dependencias externas.
- Entrada enviada mediante archivo TAR generado internamente y validado: máximo 16 archivos de texto, 96 KB, rutas relativas, sin symlinks, sin traversal.
- Salida máxima guardada 12 KB por canal, lectura por hilos para no acumular stdout ilimitado en RAM.
- El tiempo por etapa es acotado y se intenta eliminar por nombre el contenedor expirado.
- No enviar nunca a este ejecutor archivos sensibles, contraseñas, llaves, datos de alumnos ni programas obtenidos de fuentes no confiables sin revisión. Los contenedores Docker no ofrecen una garantía completa contra exploits del kernel/daemon.
- Los comandos de construcción están fijados por perfil; no se permite comando shell ni etiqueta de imagen arbitrarios enviados por el usuario.
- Los proyectos aquí admitidos son pequeños y offline; gestores de dependencias, frameworks Android/iOS, Flutter, compilación cruzada o proyectos grandes requieren pipelines y SDK adicionales verificados. No abrir acceso irrestricto al host para conseguirlo.

## Certificación verificable

Se añadió tests/test_sky_docker_builder.py con casos de autorización, rutas maliciosas, separación de pruebas, aislamiento CLI y detección honesta.
Se añadió tests/test_sky_docker_live.py, que realmente predescarga imágenes para CI y luego ejecuta Python/Node offline, prueba resultados correctos y fallos de sintaxis/salida.
Workflow: .github/workflows/sky-developer-docker.yml. El verde de CI demuestra únicamente los lenguajes y rutas allí ejercitados (Python y JavaScript). Los demás perfiles necesitan pruebas de sus propias imágenes en el dispositivo propietario.

**No hay certificación de funcionamiento en tu Windows ni Android hasta ejecutar los casos de aceptación en los dispositivos reales.**