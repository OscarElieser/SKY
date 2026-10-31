#!/usr/bin/env bash
# Verificación del APK REAL construido, no una promesa de aprobación por Play Protect.
set -euo pipefail
apk="${1:?Uso: release-security-audit.sh APK}"
build_tools="${2:-${ANDROID_HOME:?Falta ANDROID_HOME}/build-tools/35.0.0}"
test -s "$apk"
"$build_tools/apksigner" verify --verbose "$apk" >/dev/null
badging="$("$build_tools/aapt" dump badging "$apk")"
manifest="$("$build_tools/aapt" dump xmltree "$apk" AndroidManifest.xml)"
permissions="$("$build_tools/aapt" dump permissions "$apk")"
printf '%s\n' "$badging" | grep -F "package: name='ni.sky.mobileagent'" >/dev/null
if printf '%s\n' "$badging" | grep -q '^application-debuggable'; then
  echo "::error::El APK release tiene depuración habilitada"; exit 1
fi
# Exponer un servicio de accesibilidad, instalación silenciosa o lectura masiva
# sería incompatible con este binario estándar, diseñado para permisos mínimos.
if printf '%s\n' "$manifest $permissions" |
  grep -Eq 'SkyTextAssistService|SkyMusicControlService|SkyPlaybackProofListener|BIND_ACCESSIBILITY_SERVICE|BIND_NOTIFICATION_LISTENER_SERVICE|NotificationListenerService|QUERY_ALL_PACKAGES|REQUEST_INSTALL_PACKAGES|MANAGE_EXTERNAL_STORAGE|READ_SMS|RECEIVE_SMS|READ_CALL_LOG|READ_CONTACTS'; then
  echo "::error::Permiso o componente de alto riesgo en APK estándar"; exit 1
fi
for attribute in 'android:allowBackup' 'android:usesCleartextTraffic'; do
  if ! printf '%s\n' "$manifest" |
    grep -E "$attribute" | grep -Eq '(type 0x12)0x0|0x0$'; then
    echo "::error::Se requiere $attribute=false en el APK final"; exit 1
  fi
done
if ! printf '%s\n' "$manifest" | grep -q 'android:networkSecurityConfig'; then
  echo "::error::Falta política TLS explícita"; exit 1
fi
echo 'SKY Android: firma válida, sin depuración, sin servicio de accesibilidad ni NotificationListener en estándar.'
echo 'Este resultado NO acredita revisión, aceptación ni certificación de Google Play Protect.'
