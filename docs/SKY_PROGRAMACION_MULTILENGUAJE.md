# SKY Developer — programación multilenguaje verificable

**Objetivo:** permitir a SKY identificar los lenguajes solicitados y comprobar, sin inventar resultados, qué herramientas necesita un proyecto para funcionar en el equipo del dueño. Se conserva la API SKY actual y el núcleo Developer Intelligence; no se instala un servidor nuevo.

## Qué está implementado

- Catálogo de **53 lenguajes/formalismos** para detección de consultas (HTML, YAML y JSON, entre otros, son declarativos y no programas ejecutables).
- Detección de C++, C#, Go, COBOL, Kotlin, Dart, Rust, Python, MATLAB, R, Julia, Fortran, SQL y otros.
- GET /api/developer/toolchains: inspección de PATH de compiladores e intérpretes conocidos. Requiere X-SKY-KEY del propietario. No ejecuta programas ni revela rutas.
- POST /api/developer/syntax-check: sintaxis determinista de Python con ast.parse y JSON con el parser estándar. Para otros lenguajes responde requires_language_specific_toolchain.
- Pruebas unitarias y de API: no se confunde código generado con código compilado, ni un binario detectado con ejecución certificada.
- Se conservan los endpoints Developer existentes: análisis, consulta de repositorios y REPL Python.

## Consultar las herramientas instaladas

Con la API SKY iniciada y SKY_API_KEY configurada privadamente, en PowerShell:

~~~powershell
$headers = @{ "X-SKY-KEY" = $env:SKY_API_KEY }
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/developer/toolchains?language=Rust" -Headers $headers
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/developer/toolchains" -Headers $headers
~~~

Revisar código Python sin ejecutarlo:

~~~powershell
$body = @{ language = "Python"; code = "def suma(a, b): return a + b" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8765/api/developer/syntax-check" -ContentType "application/json" -Headers $headers -Body $body
~~~

El resultado syntax_valid=true valida exclusivamente la sintaxis, no el comportamiento, dependencias, seguridad, compilación, pruebas ni despliegue.

## Niveles obligatorios de evidencia

1. **Generar código:** la IA entrega una propuesta; no significa que sea correcta.
2. **Toolchain detectado:** el binario aparece en PATH; no se ha ejecutado.
3. **Sintaxis validada:** un parser real confirma la sintaxis de un archivo.
4. **Compilación verificada:** comando aislado, código de salida, logs y artefacto comprobados.
5. **Pruebas funcionales verificadas:** proyecto ejecutado en contenedor o entorno controlado con pruebas y aprobación.
6. **Despliegue certificado:** aplicación en destino real, revisión de seguridad y comprobación final.

**Esta versión implementa parte de los niveles 1–3.** No marca 4–6 como completos. Los runtimes, compiladores, paquetes, SDK, emuladores y permisos deben existir y estar autorizados. La validación móvil necesita Android/iOS reales cuando corresponda.

## Siguiente requisito para compilar y probar varios lenguajes

El ejecutor de código externo deberá usar **contenedores efímeros aislados**, sin red por defecto, usuarios no privilegiados, límites de CPU, memoria, tiempo y archivos, sin montajes privados del host ni secretos, imágenes versionadas y verificación de salida. Requiere autorización explícita del propietario antes de ejecutar código generado o descargado. No exponer un ejecutor de comandos irrestricto en la terminal Windows.

## Pruebas

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_sky_programming_capabilities.py tests/test_developer_core.py tests/test_codebase_indexer.py
~~~

El conjunto de pruebas no significa que los más de 50 lenguajes estén compilados: valida detección, autenticación, sintaxis Python/JSON y veracidad de señales.

**Política:** no borrar, reemplazar ni desactivar SKY CORE, Developer, SENTINEL, dispositivos, voz, Android ni Docencia.
