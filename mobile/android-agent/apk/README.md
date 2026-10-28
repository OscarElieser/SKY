# SKY Android 0.8.1 — APK beta firmada

**[Descargar APK de SKY Android 0.8.1 tras publicación de la Release](https://github.com/OscarElieser/SKY/releases/download/sky-android-v0.8.1/SKY-IA-Android-v0.8.1-firmada.apk)** · [Página oficial de la Release](https://github.com/OscarElieser/SKY/releases/tag/sky-android-v0.8.1) · [README Android](../README.md)

La versión **0.8.1** conserva los ojos y boca animados, los comandos supervisados de WhatsApp y añade **SKY Estudio Creativo**, con guiones y planes para redes sociales desde el teléfono. Los borradores se comparten mediante el selector oficial de Android; publicar y elegir la cuenta son decisiones del usuario. SKY Windows permanece intacto.

## Instalación en Samsung

1. Entrá a GitHub Releases desde Chrome en el Samsung y descargá el archivo `SKY-IA-Android-v0.8.1-firmada.apk` dentro de **Assets**. No hace falta descomprimir ZIP.
2. Instalá sobre la APK release anterior, si utiliza el mismo certificado; **no desinstalés** sin respaldo de claves/notas.
3. Si Google Play Protect detecta un riesgo, no desactives la protección ni forces la instalación. Revisá el mensaje exacto.
4. Comprobá ojos y boca, voz, apertura de aplicaciones y WhatsApp. Desde Ajustes, abrí **ESTUDIO CREATIVO · MIS REDES SOCIALES**, generá un borrador y revisá el menú para copiar/compartir. Ninguna publicación se envía automáticamente.
5. Si Android rechaza la actualización, compará firma y versión antes de borrar datos.

## Integridad y publicación

El workflow [SKY Android Signed Release Candidate](../../../.github/workflows/sky-mobile-release.yml) construye la variante `standardRelease` con el certificado privado configurado en GitHub Actions Secrets. Después de aprobar pruebas y firma, comprueba el paquete Android y la ausencia de `AccessibilityService` en la variante standard, genera SHA-256 y publica la APK y el archivo `.sha256` en GitHub Releases.

La Release es beta personal, no certificación ni auditoría de Google Play. Consultá la suma SHA-256 **desde la Release publicada**; no uses un valor histórico de otra versión. Los binarios debug no están destinados a actualizar una instalación release.

---

## Documentación histórica de compilaciones anteriores

Las secciones siguientes se conservan como referencia del proceso inicial.
**Para descargar o actualizar hoy, usá la guía 0.7.1 anterior.**

Esta carpeta pertenece **únicamente a la aplicación nativa Android** de SKY.
No contiene el ejecutable de Windows, ni el núcleo Python, ni las credenciales
del propietario. El código fuente está en `mobile/android-agent/app/`.

## ¿Dónde está la APK?
GitHub Actions construye la aplicación desde la rama `main` y deposita el
archivo compilado **en esta carpeta durante la compilación**, como:

```
mobile/android-agent/apk/SKY-IA-Android-standard-debug.apk
mobile/android-agent/apk/SKY-IA-Android-standard-debug.apk.sha256
```

Después publica ambos en el artefacto `sky-mobile-standard-debug` del workflow
[SKY Mobile Android Agent](../../../.github/workflows/sky-mobile-agent.yml).
Entrá en GitHub → Actions → SKY Mobile Android Agent → última ejecución
exitosa → Artifacts y descargá ese ZIP. Los APK son artefactos de compilación,
**no archivos de código fuente versionados en Git**; por eso este directorio
se mantiene en GitHub como carpeta de distribución, con una exclusión de
binarios de prueba. No supongas que una APK está lista si la compilación falla.

Para una distribución permanente corresponde publicar una Release firmada
con una clave estable, previa validación en dispositivos físicos. No se
publica automáticamente una Release de producción ni se introducen claves.


## Google Play Protect y seguridad de instalación (0.5.1)

Si Play Protect bloquea la instalación de SKY, **no deshabilites las
protecciones ni fuerces la instalación**. Guarda el texto exacto de la
advertencia, el APK y el SHA-256 para investigar el reporte.

La variante **standard** publicada por el workflow no declara ningún
`AccessibilityService` y conserva las funciones de ojos animados, voz
activada por toque, alarmas, temporizadores, notas, chat autorizado,
apertura de aplicaciones y compartir texto mediante Android.

La variante **assistive**, con el servicio opcional de escritura en campos,
es una compilación separada para revisión de seguridad y divulgaciones.
No se publica como artefacto distribuible del workflow estándar.
No se ha eliminado su código ni el núcleo Windows.

La APK standard que publica GitHub Actions **sigue siendo debug**, firmada
por una identidad de desarrollo de poca reputación; no se presenta como
release certificada. La resolución de un bloqueo de Play Protect no puede
garantizarse solo retirando un permiso. Para una distribución estable,
crear un keystore de lanzamiento privado, configurar firma reproducible,
verificar el archivo y distribuir mediante Google Play Internal Testing
u otro canal adecuado. No almacenar claves, contraseñas ni archivos
keystore en el repositorio.

**Importante:** los builds debug de GitHub pueden usar distintas firmas.
Una nueva APK puede no actualizar la instalada. No desinstalar SKY
sin preparar antes la revinculación y copia de datos locales; Android
puede borrar esos datos al desinstalar.

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

## APK de lanzamiento con firma estable y evaluación de Play Protect

No desactivar Play Protect ni forzar una instalación que fue bloqueada.
El bloqueo debe diagnosticarse con su texto exacto; la firma estable no
garantiza por sí sola que una APK vaya a ser aprobada.

El workflow manual **SKY Android Signed Release Candidate** genera
`SKY-IA-Android-standard-release.apk`, su SHA-256 y la huella pública
del certificado, sin incluir el servicio opcional de Accesibilidad. La
firma utiliza una clave privada que solo conoce el propietario. Una
compilación exitosa no equivale a aprobación de Google Play.

1. En Windows, fuera del repositorio de SKY, crear una clave persistente
   con JDK 17+ (las contraseñas se solicitan durante la ejecución):

   ```powershell
   keytool -genkeypair -v -keystore "$HOME\sky-android-release.p12" -storetype PKCS12 -alias sky-mobile -keyalg RSA -keysize 3072 -validity 3650 -dname "CN=SKY Mobile, O=SKY"
   ```

2. Guardar respaldo privado cifrado de ese archivo, alias y contraseñas.
   En GitHub, entrar a **Settings > Secrets and variables > Actions** y
   crear cuatro secretos del repositorio:

   | Secreto | Contenido |
   |---|---|
   | `SKY_ANDROID_RELEASE_KEYSTORE_B64` | Base64 de los bytes del archivo .p12 |
   | `SKY_ANDROID_RELEASE_STORE_PASSWORD` | Contraseña del almacén |
   | `SKY_ANDROID_RELEASE_KEY_ALIAS` | `sky-mobile`, o el alias elegido |
   | `SKY_ANDROID_RELEASE_KEY_PASSWORD` | Contraseña de la clave (PKCS12 normalmente usa la del almacén) |

   Para codificar el archivo con PowerShell:

   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("$HOME\sky-android-release.p12"))
   ```

   **Nunca subir ni compartir ese Base64, contraseñas o archivo privado**
   como código, issue, captura ni mensaje.

3. Abrir GitHub > Actions > **SKY Android Signed Release Candidate** >
   **Run workflow** sobre `main`. Si los secretos están ausentes, el
   proceso falla sin generar APK.
4. Si todas las pruebas aprueban, descargar el artefacto
   `sky-mobile-standard-signed-release` y verificar la suma SHA-256.
   Validar en un celular real el comportamiento y cualquier advertencia
   de Play Protect antes de distribuir la app.

La firma del APK release es distinta de la firma debug. Android no
permite actualizar in situ cuando cambian los certificados. Preparar
copia de notas y revinculación antes de considerar desinstalar una
versión configurada. La prueba CI con certificado desechable jamás se
distribuye; sirve exclusivamente para comprobar el proceso de firma.
