# Identidad visual oficial de SKY IA

Fecha de aprobación: 28 de octubre de 2026.

La marca oficial conserva el arco luminoso, red neuronal y paleta azul noche (`#061326`), plateado, cian (`#23ceff`) y azul eléctrico.

## Aplicaciones

- Logotipo SVG completo: `metaverse/static/sky-logo-oficial.svg`.
- Icono SVG: `metaverse/static/sky-icon-oficial.svg`.
- Windows: HUD (`/hud`) y asistente (`/sky`) muestran la marca oficial, sin modificar la lógica.
- Android: icono de lanzamiento adaptativo nativo y emblema en la cabecera; se conserva el personaje animado, la voz y los controles.

El recurso vectorial Android utiliza los mismos trazos de la red neuronal y el arco; su degradado se simplifica por compatibilidad con VectorDrawable. Los SVG conservan el tratamiento visual completo.

## Verificación

1. En Android, compilar `gradle -p mobile/android-agent :app:assembleStandardDebug`, verificar el icono y abrir la aplicación en un teléfono.
2. En Windows, actualizar desde `main` y reiniciar la interfaz; verificar `/hud` y `/sky`.
3. La identidad visual no cambia claves, permisos, API, procesos, escucha, paquetes ni servicios.
4. Para instalar la nueva APK se necesita generar una versión nueva, firmarla con la misma clave de distribución y volver a instalarla; un commit no actualiza automáticamente la app del teléfono.
