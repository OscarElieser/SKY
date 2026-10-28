# SKY Android — vincular Instagram mediante código temporal

Estado 28/10/2026: el servidor OAuth de Instagram está autorizado y en Supabase se guardó un token cifrado. El servidor de emparejamiento `sky-instagram` versión 11 está desplegado; el cliente Android se encuentra en `main`, pero la compilación y las pruebas en un teléfono todavía deben aprobarse.

## Seguridad

La clave `SKY_INSTAGRAM_OWNER_KEY` jamás se introduce en Android ni se publica en GitHub. El dueño la guarda en Windows con DPAPI bajo su cuenta. El teléfono recibe una credencial individual revocable cifrada con Android Keystore. El código temporal es de un solo uso y dura 10 minutos; la credencial móvil dura 30 días. Desvincular el teléfono no revoca la autorización global de Meta. No compartir código temporal, URL de OAuth o claves.

## Paso 1 — generar el código en Windows (PowerShell, cuenta donde se guardó la clave DPAPI)

```powershell
$ErrorActionPreference = "Stop"
$archivo = Join-Path $env:LOCALAPPDATA "SKY-IA\instagram-owner-key.dpapi"
$seguro = ConvertTo-SecureString -String ((Get-Content -LiteralPath $archivo -Raw).Trim())
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
try { $ownerKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
try {
  $headers = @{ Authorization = "Bearer $ownerKey" }
  $respuesta = Invoke-RestMethod -Method POST -Uri "https://jojzuaeqmjgnqikpnfxk.supabase.co/functions/v1/sky-instagram/pair-create" -Headers $headers -ContentType "application/json" -Body '{}' -ErrorAction Stop
  Write-Host "Código temporal para SKY Android:" $respuesta.pairing_code
  Write-Host "Vence en" $respuesta.expires_in_seconds "segundos."
} finally { Remove-Variable ownerKey,headers,seguro -ErrorAction SilentlyContinue }
```

## Paso 2 — en SKY Android

Abrir **Ajustes → Mis redes → Instagram → Conexión segura con Instagram → Vincular este teléfono con código temporal**. Introducir el código recibido (solo 18 caracteres hexadecimales). No introducir claves Meta ni del propietario.

Después pulsar **Consultar conexión verificada**. El estado se obtiene de Supabase y muestra los permisos del token. Todavía indica que la identidad exacta del perfil no está verificada. Se debe completar la verificación de perfil por API antes de habilitar publicaciones, comentarios o mensajes.

Para revocar el dispositivo: **Desvincular este teléfono**. Para revocar el acceso Meta, revocarlo además desde permisos de Instagram.

## Límite del alcance actual

El emparejamiento y la consulta de estado no implementan ni habilitan publicación/mensajería. Falta revisión de seguridad, validación de identidad real y renovación del token Meta. Compilación CI y prueba manual pendientes. Ningún módulo Windows ni proyecto BAQUEANO fue modificado.
