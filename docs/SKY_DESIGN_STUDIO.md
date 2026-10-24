# SKY Design Studio — interfaces originales animadas para web y Flutter

SKY conserva su API propia, el HUD, su núcleo, seguridad SENTINEL, voz, docencia, teléfono y herramientas de programación anteriores. Este módulo **no** ejecuta código generado sin autorización ni instala dependencias indiscriminadamente en el núcleo SKY.

## Qué se agregó

- **Generador real React:** devuelve un proyecto editable de React + Vite con bibliotecas declaradas de forma exacta en `package.json`: React, React DOM, Motion para animaciones, Lucide React para iconos vectoriales y Fontsource Inter para tipografía. El proyecto no depende de un CDN externo para cargar iconos ni fuentes en producción.
- **Generador real Flutter:** devuelve aplicación Flutter Material 3 adaptable a móvil/web/escritorio, con biblioteca `flutter_animate` fijada a 4.5.2, componentes y pruebas de widgets, navegación y filtros. Los iconos proceden de Material Icons incluidos en Flutter.
- **Identidad visual:** identifica sectores turismo, docencia, salud, finanzas, videojuegos, cultura y tecnología. Adapta títulos, tarjetas, propósito y texto. Una huella del título y descripción escoge paleta/estética/estructura; el usuario también puede fijar estilo y estructura. La paleta no se improvisa a partir de código libre.
- **Animaciones con propósito:** microinteracciones, órbitas, tarjetas, entradas y controles reales. React contempla `prefers-reduced-motion`; Flutter consulta la preferencia de reducción de animaciones del dispositivo.
- **Interacción real local:** navegación interna, filtros, diálogos y botones explícitos. Las integraciones con negocio (reservas, pagos, registros o backend) no se simulan; quedan marcadas como demostrativas hasta conectar un servicio real.
- **Archivo ZIP real:** los fuentes editables se devuelven en ZIP bajo pedido y sin alterar ficheros del equipo propietario.

## SKY API privada (sin servidores paralelos)

- GET `/api/developer/design/capabilities`
- POST `/api/developer/design/create`: cuerpo JSON: `{"title":"Ruta Viva","brief":"Plataforma de turismo sostenible con rutas locales","platform":"react","style":"aurora","layout":"immersive"}`. También `platform:"flutter"`. Valores opcionales `style`: auto, aurora, ember, monochrome. `layout`: auto, editorial, dashboard, immersive. `domain`: auto o identificador del sector.
- POST `/api/developer/design/download`: mismos datos de entrada; devuelve ZIP (`application/zip`) con archivos y manifest técnico, sin acciones sobre disco.

Todos usan la autenticación y segundo factor de SKY. Los estilos y mensajes ingresados se tratan como datos, no como código de usuario que deba ejecutarse. El generador solo lee una pequeña lista de plantillas locales controladas por el repositorio.

## Uso dentro del HUD

Abrir **SKY → Programación → SKY Design Studio**. Escribir el nombre del producto y un propósito claro. Seleccionar Web React o Flutter, estilo y distribución. Presionar **Crear diseño real**, revisar paquetes y archivos, y **Descargar proyecto ZIP**. La ejecución/build ocurre después con SDK en un proyecto separado:

React:

```bash
npm install --ignore-scripts --no-audit --no-fund
npm run build
npm run dev
```

Flutter:

```bash
flutter pub get
flutter analyze
flutter test
flutter run
```

Es posible que una plantilla Flutter tenga que generarse con el esqueleto Android/iOS mediante `flutter create .` en un entorno Flutter **antes** de compilar un APK o proyecto iOS; la descarga ZIP contiene código y dependencias de la app y NO presume archivos nativos ya creados.

## Pruebas y límites verificados

- `tests/test_sky_design_studio.py`: cambios de identidad por sector, seguridad ante entradas extrañas, bibliotecas declaradas y versiones exactas, ZIP sin traversal, autorización de API y estados verdaderos.
- `.github/workflows/sky-design-studio.yml`: instala dependencias React **solo en el proyecto de prueba CI**, realiza build Vite real, inspecciona los artefactos, y ejecuta `npm audit --omit=dev --audit-level=high`; para Flutter, instala SDK real, resuelve flutter_animate, corre `flutter analyze`, `flutter test` y compila **Flutter web** si el runner lo permite.
- No se han probado navegadores móviles, dispositivos físicos, tiendas Play/App Store, accesibilidad con lectores reales de pantalla ni carga de producción mediante estos tests. Tampoco se afirma que el servicio de backend exista para botones demostrativos.
- Un diseño generado no es necesariamente único en sentido de propiedad intelectual, ni comparable automáticamente a trabajo profesional sin revisión visual y pruebas con usuarios. La identidad depende del briefing y del diseño seleccionado; SKY puede iterar con distintas paletas/distribuciones.

## Bibliotecas verificables y procedencia

- https://motion.dev/docs/react-installation
- https://lucide.dev/guide/packages/lucide-react
- https://fontsource.org/fonts/inter
- https://vite.dev/guide/
- https://pub.dev/packages/flutter_animate
- https://docs.flutter.dev/ui/animations

El generador no sustituye el sistema de compilación protegido por PIN de SKY ni elimina ninguna herramienta anterior.
