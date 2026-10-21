# SKY JARVIS local — primera fase funcional (Windows)

Esta integración permite **ejecutar realmente** órdenes de bajo riesgo por voz: «SKY, abre YouTube», «SKY, abre la calculadora», «SKY, abre el bloc de notas» y «SKY, consulta el estado de mi computadora». Reutiliza el agente autorizado del repositorio; no representa control total del sistema.

## Preparar Windows

1. Instalar Python y las dependencias de SKY. Además instalar `vosk`, `sounddevice` y `pyttsx3` en el mismo entorno: `python -m pip install vosk sounddevice pyttsx3`.
2. Descargar un modelo español de Vosk de su distribución oficial y extraerlo en `modelos/vosk-model-es`, o pasar como argumento la carpeta donde esté instalado.
3. Ejecutar `INICIAR_SKY_JARVIS_WINDOWS.bat` desde una sesión interactiva de Windows. Inicia el agente HTTP local con token y el escucha de voz con la opción explícita `--execute-safe`.
4. Hablar después de decir **SKY**. El sistema solo ejecuta `status`, `open_url` (HTTPS) y las cuatro aplicaciones de la lista permitida y las teclas multimedia de Windows (reproducir/pausar, pista siguiente/anterior y volumen). Si el agente no está funcionando, dirá que no puede ejecutar la orden.
5. Ctrl+C detiene el reconocimiento. Cerrar la ventana separada del agente detiene el acceso al dispositivo.

También se admite el arranque manual en dos terminales: `python agente_dispositivo.py` y `python sky_manos_libres.py --model modelos/vosk-model-es --execute-safe`.

## Windows: WinError 10013 al arrancar agente_dispositivo.py

El puerto heredado `8765` puede estar reservado por Windows, WSL/Hyper-V u otro servicio SKY. El lanzador `INICIAR_SKY_JARVIS_WINDOWS.bat` configura por defecto `SKY_DEVICE_PORT=18765` **para el agente y la voz**, siempre que no exista ya una elección explícita en el entorno. No se cambia el puerto de SKY Engine.

Si se inicia manualmente, fijar el **mismo puerto en ambas terminales** antes de iniciar los procesos:

```powershell
$env:SKY_DEVICE_PORT = "18765"
python agente_dispositivo.py
```

En una segunda terminal PowerShell:

```powershell
$env:SKY_DEVICE_PORT = "18765"
python sky_manos_libres.py --model modelos/vosk-model-es --execute-safe
```

Para diagnosticar bloqueos de puerto sin deshabilitar protección de Windows:

```powershell
Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue
netsh interface ipv4 show excludedportrange protocol=tcp
```

El puerto debe permanecer enlazado solo a `127.0.0.1`. En el panel Streamlit, si se empareja la misma PC manualmente, usar `http://127.0.0.1:18765` y el token privado del agente. Si también está bloqueado `18765`, elegir otro puerto local disponible y configurarlo de forma consistente. No abrir puertos, desactivar el firewall ni ejecutar como administrador para eludir la restricción.

## Panel Streamlit

En **Dispositivos → Voz**, el usuario puede marcar la opción de ejecución directa de acciones simples cuando existe un dispositivo emparejado y autenticado. Por defecto sigue la confirmación manual. El navegador remoto no controla Windows por sí mismo: el agente debe estar ejecutándose en el PC destinatario.

## Política de autorizaciones

- **Sin confirmación adicional, solo tras activar el modo:** abrir una web HTTPS conocida, lanzar una app de lista permitida o consultar estado.
- **Requieren confirmación por acción y permisos acotados (no incluidos en esta fase):** crear/editar/borrar archivos, envío de emails/mensajes, automatizar formularios, cambiar configuraciones e instalar aplicaciones.
- **Nunca autorizar mediante un prompt:** ejecución arbitraria de PowerShell, extracción de contraseñas/tokens, acceso a datos de terceros, eludir UAC o seguridad del sistema, control de cuentas sin inicio de sesión legítimo.

Integrar correo con OAuth y API oficial (por ejemplo Gmail); mensajería con proveedores autorizados. Una IA que redacta no demuestra que envió. Tras enviar, comprobar respuesta real del proveedor y conservar auditoría con información mínima.

### Limitaciones verificadas

La versión no incluye todavía lectura/escritura de archivos de usuario, envío de mensajes, control de móviles ni automatización de ventanas no autorizadas. El modo manos libres necesita un micrófono funcional y modelo Vosk local instalado; no se ha probado en el equipo particular del propietario.


## Teclas multimedia, sin simulación de resultados

Con el modo seguro autorizado se pueden decir «SKY, pausa la música», «SKY, siguiente canción», «SKY, baja volumen» y «SKY, silencia». Se envían **teclas multimedia nativas de Windows**, sin ejecutar PowerShell ni comandos arbitrarios. La respuesta confirma únicamente que se envió la tecla; no garantiza que exista un reproductor activo ni que cambie su estado. El comando «reproduce» es un alternador reproducir/pausar, no busca títulos o artistas específicos.

Las acciones de crear, modificar o borrar documentos **no están autorizadas en modo manos libres**. Para incorporarlas se debe crear un módulo de documentos con carpeta de trabajo limitada, vista previa, confirmación humana antes de sobrescribir/borrar, copias de seguridad y pruebas que impidan escape de rutas. La fase actual no permite borrar archivos por error de transcripción.


## Notas locales (texto y papelera recuperable)

El agente puede crear notas, agregar texto y moverlas a papelera solamente dentro de ~/.neuralt/notes (perfil local de Windows). No accede por este medio a otras carpetas.

Por seguridad viene desactivado. Para activarlo hay que cerrar el agente, ejecutar set SKY_NOTES_ENABLED=1 en una ventana CMD y volver a iniciar el agente desde esa ventana. No se almacena este permiso en el repositorio.

Ejemplos de órdenes: «SKY, crea una nota agenda que diga reunión el lunes», «SKY, agrega a la nota agenda el texto llevar computadora», «SKY, elimina la nota agenda». Cada acción se pone en pendiente y debe revisarse y confirmarse desde el panel de SKY. Incluso con el modo manos libres --execute-safe, las acciones de escritura nunca se ejecutan automáticamente.

El contenido de una nota se limita a 12 000 caracteres por orden y el archivo a 64 KB. No se admiten nombres de ruta, extensión arbitraria ni enlaces simbólicos. La creación no sobrescribe archivos existentes y la eliminación conserva copia recuperable en .trash. No significa que SKY ya pueda editar documentos externos, aplicaciones o correos.
