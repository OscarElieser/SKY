# SKY Developer Workbench — ingeniería universal con evidencia

El objetivo es ayudar a crear, comprender, corregir y auditar programas sin inventar éxitos. Mantiene la API FastAPI, SKY SENTINEL, la interfaz holográfica, Docencia, voz y los 14 perfiles Docker previos.

## Inventario real

El catálogo de SKY contiene decenas de lenguajes y tecnologías declarativas, entre ellos HTML5, CSS3, JavaScript, TypeScript, Python, C/C++, C#, Dart, Kotlin, Swift, Go, Rust, Java, SQL, COBOL, GDScript y muchos más. Algunos son formatos (JSON/YAML/HTML) o tipos de proyecto (Web), no lenguajes ejecutables. No se declara que todos estén compilados o puedan ejecutarse localmente.

El nuevo módulo incorpora referencias oficiales a React, Next.js, Vue, Angular, Tailwind CSS, Flutter, React Native, SwiftUI, Jetpack Compose, Unity, Unreal Engine, Godot, PyTorch, TensorFlow, Supabase, PostgreSQL, MySQL, Firebase, MongoDB, VS Code, Visual Studio, Android Studio, Xcode, Lucide, Material Symbols, Font Awesome, Heroicons, Bootstrap Icons, Iconify, Phosphor, Google Fonts, Fontsource, Inter, Noto Sans, JetBrains Mono y otros.

Estas referencias NO acreditan instalación, compatibilidad, licencia, seguridad o pruebas. Las bibliotecas y fuentes deben elegirse caso por caso, con procedencia oficial, versión, licencia, alternativas y fallbacks.

## Funciones nuevas en la API SKY existente

- GET /api/developer/workbench/catalogue?category=frameworks&query=Flutter — referencias por categorías languages, frameworks, databases, ides, icons, fonts. Incluye indicador explícito de no instalación y enlace a documentación original.
- GET /api/developer/workbench/readiness — detecta comandos en PATH para Flutter/Dart, Android adb, Xcode, Unity, Godot, Unreal Build Tool, VS Code, Visual Studio, Java, .NET, Docker, Git, Python y otros. No invoca nada; un programa puede estar instalado fuera del PATH y detectarse como no encontrado.
- POST /api/developer/workbench/inspect — analiza de forma estática archivos de proyecto recibidos en memoria, hasta 36 archivos y 240 KB. Reconoce package.json, requirements.txt, pyproject.toml, pubspec.yaml, Cargo.toml, Unity Packages/manifest.json, Godot project.godot, Unreal .uproject y Android/Gradle. No ejecuta ni instala.
- POST /api/developer/workbench/explain — explica cada línea del código en español con paginación, numeración y contexto superficial, sin modificar el original. Es análisis estático orientativo; no se confunde con conocimiento semántico completo ni pruebas.
- POST /api/developer/workbench/starter/web — genera en memoria HTML5 + CSS3 + JavaScript sin dependencias externas, con diseño adaptable, accesibilidad básica e interacción. Se añadió una prueba real de la plantilla en el Docker Web anterior.
- GET /api/developer/workbench/packages/lookup?registry=npm&name=lucide-react — consulta metadatos de npm, PyPI y pub.dev sin descargar ni instalar paquetes. Está deshabilitada hasta que el propietario active SKY_DEV_REGISTRY_LOOKUP_ENABLED=1. Utiliza HTTPS, hosts oficiales fijos, validación de nombres, límites de respuesta, tiempo de espera y sin redirecciones.

Los endpoints se protegen con el sistema de autenticación y segundo factor de SKY existente. Los editores de SKY → Programación ahora incluyen explorador de tecnologías, revisión SDK, plantilla web, consultor de paquetes, inspección de proyectos y explicación línea por línea. La ejecución dentro de Docker conserva aprobación, PIN, aislamiento, límites de recursos y opt-in.

## Sobre las bibliotecas de iconos y tipografías

SKY puede mostrar documentación autorizada y consultar de forma voluntaria metadatos publicados en npm y pub.dev (por ejemplo lucide-react, react-icons, google_fonts, flutter_svg). Esto NO quiere decir que todos esos paquetes hayan sido instalados o funcionen con cualquier proyecto. No cargar scripts de CDNs desconocidos ni descargar fuentes sin autorización y verificación de licencia. Comprobar la resolución de iconos concretos y fallback de tipografía en un navegador o dispositivo real.

Documentación de registros:
- https://docs.npmjs.com/using-npm/registry.html
- https://docs.pypi.org/api/json/
- https://pub.dev/help/api

## Limitaciones explícitas y pruebas futuras

Para crear APK/AAB Android o compilar para iOS se requieren SDK y dispositivo/emulador; Xcode y firma iOS exigen macOS. Unity, Godot y Unreal requieren motor real, licencia y pipeline específico. Flutter requiere flutter doctor, flutter analyze, flutter test y flutter build en equipo autorizado. Los frameworks con dependencias necesitan instalación controlada, versiones fijadas, auditoría de vulnerabilidades, tests reales, análisis de licencia y despliegue aprobado.

No existe una cantidad finita y estable de todas las librerías de software del mundo. SKY no debe prometer cero errores ni simular que un proyecto se probó; los 14 perfiles Docker anteriores y las nuevas referencias de conocimiento se informan por separado.

Pruebas: tests/test_sky_developer_workbench.py, tests/test_sky_web_live.py y los flujos de GitHub Actions sky-developer-workbench.yml y sky-developer-docker.yml.

SKY conservará la API existente y no eliminará los módulos de voz, dispositivos, Docencia, seguridad, teléfonos ni el historial de GitHub.
