# Instalación completa de dependencias de SKY IA (Windows 10/11)

Este repositorio tiene un **inventario maestro** y un **instalador de una sola ejecución** para replicar una instalación en otro equipo Windows. La instalación usa versiones y rangos declarados, no distribuciones binarias guardadas en GitHub.

## Archivos oficiales

- `requirements_sky_all.txt`: agrega **todos los perfiles Python declarados**, incluido el núcleo, las bibliotecas de voz y los componentes de investigación/LoRA. Lee de los manifiestos existentes: no los modifica.
- `INSTALAR_DEPENDENCIAS_SKY.ps1`: instalador único de PowerShell para Python, dependencias Node y Flutter cuando corresponda; con opción de herramientas externas vía winget y Ollama local.
- `scripts/sky_dependencias_todas.py`: revisa requisitos Python recursivos y sus versiones **sin internet**. Los extras de pip no se consideran plenamente comprobados hasta una resolución/instalación efectiva.
- `requirements_verified_v110.txt`: instantánea de referencia para Python 3.11, **no** se aplica automáticamente para evitar sobrescribir el entorno actual con versiones fijadas para otra línea de pruebas.

## Una computadora nueva: instalación en un comando

Descargá/cloná el repositorio de GitHub en la PC nueva. Si el PC no tiene Git, podés empezar descargando el ZIP del repositorio desde GitHub y extraerlo, o instalar Git previamente.

Abrí PowerShell **dentro de la carpeta SKY**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\INSTALAR_DEPENDENCIAS_SKY.ps1" -Perfil Completo -Herramientas
```

Este comando intenta instalar todos los paquetes Python del inventario, las tres colecciones npm existentes, dependencias Flutter cuando `flutter` esté disponible y las herramientas Windows detectadas como ausentes. La opción `-Herramientas` autoriza expresamente instalaciones winget de Git, Node LTS, JDK 17, FFmpeg, Tailscale, Ollama, Flutter y Android Studio; pueden ser descargas grandes, requerir privilegios, licencias, reiniciar PowerShell o completar configuración adicional. Tras instalar programas externos, es posible que **debás ejecutar el mismo comando una segunda vez** para que PowerShell detecte el PATH actualizado. No borra nada ni fuerza `pip --upgrade`.

Al finalizar, si hubo herramientas no disponibles o tareas opcionales pendientes, el instalador lo indica y retorna código distinto de cero. *Un proceso ejecutado no garantiza que todos los SDK funcionen hasta probarlos*.

### Perfil para la PC de casa (i3, 8 GB RAM, SSD)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\INSTALAR_DEPENDENCIAS_SKY.ps1" -Perfil Casa
```

Instala los paquetes del `requirements.txt` existente, usando `.venv`. **No instala todos los opcionales**, ni ejecuta Node/Flutter. Importante: el núcleo actual **incluye PyTorch** y puede consumir bastante disco y RAM; todavía no equivale a un núcleo mínimo sin modelos pesados.

### Opcional: modelo Ollama según RAM

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\INSTALAR_DEPENDENCIAS_SKY.ps1" -Perfil Completo -Herramientas -ModeloOllama
```

`-ModeloOllama` elige `qwen2.5:3b` en menos de 16 GB RAM o `qwen2.5:7b` desde 16 GB. Consulta el inventario local de Ollama y evita repetir `pull` si el modelo ya está. No se instala silenciosamente.

### Verificar SIN instalar ni descargar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\INSTALAR_DEPENDENCIAS_SKY.ps1" -Perfil Completo -SoloVerificar
```

Examina localmente el manifiesto recursivo y ejecuta `pip check`. El verificador marca `extras_sin_verificar` cuando no puede probar todos los paquetes adicionales que una variante `[extra]` instala; no afirma una instalación completa únicamente por encontrar la distribución principal.

## ¿Qué está incluido?

| Ecosistema | Manifiesto original / instalación |
| --- | --- |
| CORE, API, HUD, Python y clientes de IA | `requirements.txt` |
| Metaverso, aplicaciones y Office | `requirements_social.txt`, `requirements_office.txt`, `requirements_studio.txt` |
| Producción, Redis (cliente Python) | `requirements_production.txt` |
| Investigación y entrenamiento LoRA | `requirements_sky_training.txt` |
| CrewAI, AutoGen, LangChain, utilidades de agentes | `requirements_sky_optional_integrations.txt` |
| Conectividad mDNS/BLE y protocolo MCP | `requirements_connectivity_optional.txt`, `requirements_mcp_optional.txt` |
| Conversión documental MarkItDown con PDF/Office | `requirements_markitdown_optional.txt` |
| Voz local (librerías Python) | faster-whisper, Vosk, sounddevice, pyttsx3, pywin32 |
| Desarrollo y pruebas | pytest |
| Frontend y vídeo JS | `sky_d3/package.json`, `sky_remotion/package.json`, `templates/sky_design_react/package.json` |
| Flutter | `templates/sky_design_flutter/pubspec.yaml`; `flutter pub get` si el SDK está disponible |
| Kotlin/Android | JDK 17, Android Studio, Android SDK 35, build-tools 35.0.0 y Gradle 8.11.1 |
| Herramientas externas | Git, Node/npm, Flutter, Tailscale, FFmpeg, Ollama (opcionales vía winget) |

## No se incluyen secretos ni binarios gigantes en GitHub

- `.env`, tokens, claves de APIs y códigos de emparejamiento nunca deben subir al repositorio. Configuralos localmente después.
- Ollama, modelos de voz Piper/Whisper/Vosk y otros pesos son archivos descargables específicos de cada máquina. El instalador Python incluye bibliotecas de voz, **no los modelos**. El instalador existente `instalar_sky.ps1` mantiene el procedimiento opcional para los modelos de voz.
- Redis **servidor**, Docker Desktop, licencias Android, SDK Android 35, Gradle 8.11.1, GPU CUDA, modelos LoRA entrenados y permisos del sistema requieren configuración y pruebas independientes; instalar el paquete Python no los proporciona.
- Instalar Tailscale no vincula automáticamente dispositivos ni publica la API. SKY debe atender en `127.0.0.1`, usando posteriormente red privada y autenticación. Nunca expongás 8765/8766 directamente.
- Puede haber incompatibilidades entre bibliotecas opcionales, versiones de Python y hardware. El perfil completo **no tiene garantía de resolver todas las combinaciones** sin validación por máquina.
- Este instalador no arranca SKY, no registra servicios 24/7, no modifica el PIN ni cambia permisos de dispositivos. Es solo instalación de dependencias.

## Actualizar el código existente de Antigravity SIN perder cambios

```powershell
Set-Location "D:\Desktop\SKY"
git status --short
git fetch origin
```

Si el árbol local está limpio y estás en `main`:

```powershell
git pull --ff-only origin main
```

Si Antigravity tiene cambios locales, primero guardalos en su rama/commit y evitá `reset --hard`. El repositorio conserva todos los manifiestos anteriores. El nuevo archivo maestro solamente los reúne.

## Verificación de este cambio

GitHub Actions valida el inventario recursivo y su sintaxis, además de comprobar la sintaxis de PowerShell sin ejecutar descargas. La instalación completa no se puede certificar sin ejecutarla en cada Windows objetivo y medir su compatibilidad (particularmente Python, GPU, Android y conectores externos).
