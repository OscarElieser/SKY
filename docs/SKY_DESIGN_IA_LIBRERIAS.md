# SKY Design Studio — IA creativa y librerías instalables de verdad

Esta extensión utiliza la **API propia de SKY**, el sistema de autenticación actual y el gateway de IA existente (`neural_core.providers`). Conserva todos los módulos anteriores.

## Qué cambió

SKY ahora puede tomar la descripción concreta del usuario y pedir a un modelo de IA una propuesta de dirección artística para un producto. El resultado contiene textos relevantes, objetivos de tres tarjetas, iconos verificados, selección de tema y disposición; se integra a un proyecto editable **React** o **Flutter**. No ejecuta instrucciones arbitrarias producidas por el modelo ni modifica los archivos del equipo por sí sola.

El modo IA **requiere una acción expresa**. Por defecto usa **Ollama local**, y no se conmuta silenciosamente a proveedores de nube. Si se elige OpenAI, Claude, Gemini u otro proveedor remoto, se necesita marcar consentimiento y aprobar la solicitud. Solo se envían el título y la descripción del diseño, no archivos, claves, conversaciones privadas ni el código de la computadora. Si no hay proveedor activo, SKY informa el error: no finge que un modelo respondió.

### Endpoints

- `POST /api/developer/design/ai/create`: cuerpo de ejemplo:
  `{"title":"Ruta Viva","brief":"Web para turismo rural sostenible","platform":"react","provider":"ollama","approved":true}`
- Para uso con nube agregar `"provider":"anthropic","allow_cloud":true` **con aprobación explícita**. La clave del proveedor debe existir en la configuración privada de SKY.
- `POST /api/developer/design/download`: enviar título, brief y demás opciones más el `design_plan` devuelto por el primer endpoint para bajar exactamente el diseño que propuso la IA, sin pagar dos veces ni volver a enviar el texto a la nube.
- Se conservan `/api/developer/design/create` para propuestas locales basadas en reglas y `/api/developer/design/capabilities`.

La salida de IA se valida como JSON con límites de longitud y un conjunto de iconos, layouts y paletas permitidos. Una respuesta inválida **falla explícitamente** y no se reemplaza en silencio por otra. Esto genera propuestas personalizadas y reales dentro del motor de plantillas, no afirma creatividad visual ilimitada ni invención de cualquier interfaz desde cero.

## Dónde y cómo se instalan las bibliotecas

No es correcto instalar todas las librerías existentes a nivel global en la carpeta de SKY: sería inestable, inseguro y ocuparía mucho espacio. Las bibliotecas se instalan en **el proyecto que las necesita**.

| Plataforma | Biblioteca | Función |
| --- | --- | --- |
| React | `react`, `react-dom` | Componentes y estado |
| React | `motion` | Animaciones |
| React | `lucide-react` | Iconos SVG |
| React | `@fontsource/inter` | Tipografía autohospedada con fallback |
| React | `vite` | Servidor de desarrollo y compilador |
| Flutter | `flutter_animate` | Animaciones |
| Flutter | Material Icons / Material 3 | Iconografía y componentes del SDK |

Los archivos `package.json` y `pubspec.yaml` contienen versiones declaradas en el proyecto. La compilación real en GitHub instala esas dependencias y verifica si funcionan; no significa que se encuentren instaladas en el equipo del usuario.

### Preparación voluntaria del proyecto en Windows

1. Abrí **SKY → Programación → SKY Design Studio**, elegí web o Flutter y creá el proyecto.
2. Seleccioná **Descargar proyecto ZIP** y extraelo en una carpeta separada.
3. Revisá el archivo `sky-preparar.ps1` incluido; desde PowerShell en esa carpeta ejecutá `./sky-preparar.ps1`.
4. El script mostrará las bibliotecas y **pedirá escribir INSTALAR**. Sin esa confirmación no descarga paquetes. React ejecuta `npm install --ignore-scripts` y `npm run build`. Flutter genera el esqueleto web/Android si hace falta y corre `flutter pub get`, `flutter analyze` y `flutter test`.

Es necesario tener instalado Node.js/npm o el SDK de Flutter. El comando npm instala únicamente en el proyecto; no utiliza `npm install -g`. Estos procesos necesitan acceso a Internet y pueden descargar múltiples archivos. Antes de instalar dependencias, el propietario debe revisar las licencias, la cadena de suministro y la confiabilidad de los paquetes.

## Qué validamos

La suite de pruebas de SKY simula la **respuesta de IA** para validar el contrato de privacidad, los JSON, los iconos permitidos, la protección ante inyección y la reproducción exacta del ZIP. **No confirma que las credenciales personales del usuario funcionen**, ni la calidad de todo modelo de IA.

Separadamente, la CI toma especificaciones creativas estructuradas, construye proyectos **React/Vite** y **Flutter Web** con librerías reales, corre los tests y reporta fallos. No se afirma una publicación en App Store, Play Store ni una ejecución física de Android o iPhone.

Las versiones de iconos, tipografías, SDK y dependencias deben actualizarse cuando sea necesario y comprobarse nuevamente antes de publicar. No se puede prometer que todo diseño es único en sentido legal ni que ninguna biblioteca tendrá errores.

Referencia: `tests/test_sky_design_ai.py`, `tests/test_sky_design_studio.py`, `.github/workflows/sky-design-studio.yml`, `docs/SKY_DESIGN_STUDIO.md`.
