# SKY Android — descargar, verificar e instalar la APK 0.7.1

**Última beta personal publicada:** SKY Aura Premium **0.7.1**. El código de Android vive en [`mobile/android-agent/`](../); **no modifica SKY Windows**.

[**⬇ Descarga directa firmada (.apk)**](https://github.com/OscarElieser/SKY/releases/download/sky-android-v0.7.1/SKY-IA-Android-v0.7.1-firmada.apk) · [Página de la Release](https://github.com/OscarElieser/SKY/releases/tag/sky-android-v0.7.1) · [Instrucciones del teléfono](../README.md)

**Datos verificados en GitHub (Release 0.7.1):**
- Archivo: `SKY-IA-Android-v0.7.1-firmada.apk`
- Tamaño: 706405 bytes · Android `versionCode=12` · variante `standard`.
- SHA-256: `73ab848a8f5c74367d78199b86bc1e765c338f7fe951d237b07853fb363c28cf`
- [Archivo SHA-256 publicado](https://github.com/OscarElieser/SKY/releases/download/sky-android-v0.7.1/SKY-IA-Android-v0.7.1-firmada.apk.sha256)
- La firma y el manifiesto de la variante estándar se verifican antes de publicar. **Esto no implica certificación de Google Play ni pruebas completas en un dispositivo real.**

## Instalación desde Samsung Android

1. Abrí la **página de Releases** en Chrome, desplegá **Assets** y elegí `SKY-IA-Android-v0.7.1-firmada.apk`. No hace falta extraer ZIP ni descargar artefactos de GitHub Actions.
2. Abrí el APK desde **Mis archivos → Descargas**. Si ya tenés SKY firmada con la misma clave, instalá encima sin desinstalar.
3. Si Android indica `App not installed`, puede haber incompatibilidad de firma. **No desinstalés ni borres datos** sin respaldo. Revisá versión, origen y huella del certificado.
4. Si Google Play Protect bloquea o advierte sobre un riesgo, **no lo desactives ni forces la instalación**. Guardá el mensaje exacto para revisar la seguridad y el canal de distribución.
5. Abrí SKY → Ajustes; el modo de Gemini funciona por internet independientemente de Windows. La clave se introduce **solo en el teléfono** y no debe enviarse por chats o GitHub.

## Cómo se publica cada APK

- [Workflow firmado](../../../.github/workflows/sky-mobile-release.yml): `SKY Android Signed Release Candidate`, activado al cambiar `mobile/android-agent/**` en `main` o manualmente.
- Ejecuta tests, compila `standardRelease`, comprueba paquete, firma, ausencia del servicio de accesibilidad y genera SHA-256/huella de certificado.
- Publica `sky-mobile-standard-signed-release` en Actions y, tras las comprobaciones, crea una **prerelease** con APK directa y archivo SHA-256 en [GitHub Releases](https://github.com/OscarElieser/SKY/releases).
- La clave privada de firma vive en **GitHub Actions Secrets**; no se versiona. No reutilizar una versión para publicar otra compilación distinta: aumentar `versionName`/`versionCode`.
- Los artefactos `debug` son para desarrollo y pueden tener firmas diferentes: **no deben instalarse encima de una APK release existente**.
- La variante `standard` no incluye servicio de Accesibilidad; las capacidades asistidas más amplias requieren revisión de permisos y una distribución separada.

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
