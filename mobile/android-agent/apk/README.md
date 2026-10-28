# SKY IA — APK Android (distribución separada)

Esta carpeta pertenece **únicamente a la aplicación nativa Android** de SKY.
No contiene el ejecutable de Windows, ni el núcleo Python, ni las credenciales
del propietario. El código fuente está en `mobile/android-agent/app/`.

## ¿Dónde está la APK?
GitHub Actions construye la aplicación desde la rama `main` y deposita el
archivo compilado **en esta carpeta durante la compilación**, como:

```
mobile/android-agent/apk/SKY-IA-Android-debug.apk
mobile/android-agent/apk/SKY-IA-Android-debug.apk.sha256
```

Después publica ambos en el artefacto `sky-mobile-agent-debug` del workflow
[SKY Mobile Android Agent](../../../.github/workflows/sky-mobile-agent.yml).
Entrá en GitHub → Actions → SKY Mobile Android Agent → última ejecución
exitosa → Artifacts y descargá ese ZIP. Los APK son artefactos de compilación,
**no archivos de código fuente versionados en Git**; por eso este directorio
se mantiene en GitHub como carpeta de distribución, con una exclusión de
binarios de prueba. No supongas que una APK está lista si la compilación falla.

Para una distribución permanente corresponde publicar una Release firmada
con una clave estable, previa validación en dispositivos físicos. No se
publica automáticamente una Release de producción ni se introducen claves.

## PC y celular conectados, pero con código separado
- **Windows:** conserva el motor, HUD, agentes, memoria y herramientas
  existentes en sus propias rutas.
- **Android:** tiene interfaz de ojos animados, micrófono, voz, chat y
  permisos propios del dispositivo.
- **Puente compartido:** ambos utilizan las API existentes de SKY Core a
  través de HTTPS privado autenticado. Android nunca recibe la clave
  maestra de Windows; usa tokens limitados de dispositivo y chat.

La vinculación del teléfono se conserva cifrada mediante Android Keystore.
La autorización temporal del chat se renueva por separado. Las órdenes para
abrir aplicaciones necesitan consentimiento por aplicación y por acción.
La voz de Android y los accesos rápidos no equivalen a replicar todas las
herramientas de Windows ni garantizan funcionamiento cuando SKY Core
esté desconectado.

**Actualizaciones:** los APK debug de distintas máquinas de GitHub Actions
pueden tener firmas incompatibles. Conservá el código de vinculación y una
vía para recuperar el acceso antes de desinstalar una versión ya configurada.
