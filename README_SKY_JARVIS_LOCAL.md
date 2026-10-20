# SKY JARVIS local — primera fase funcional (Windows)

Esta integración permite **ejecutar realmente** órdenes de bajo riesgo por voz: «SKY, abre YouTube», «SKY, abre la calculadora», «SKY, abre el bloc de notas» y «SKY, consulta el estado de mi computadora». Reutiliza el agente autorizado del repositorio; no representa control total del sistema.

## Preparar Windows

1. Instalar Python y las dependencias de SKY. Además instalar `vosk`, `sounddevice` y `pyttsx3` en el mismo entorno: `python -m pip install vosk sounddevice pyttsx3`.
2. Descargar un modelo español de Vosk de su distribución oficial y extraerlo en `modelos/vosk-model-es`, o pasar como argumento la carpeta donde esté instalado.
3. Ejecutar `INICIAR_SKY_JARVIS_WINDOWS.bat` desde una sesión interactiva de Windows. Inicia el agente HTTP local con token y el escucha de voz con la opción explícita `--execute-safe`.
4. Hablar después de decir **SKY**. El sistema solo ejecuta `status`, `open_url` (HTTPS) y las cuatro aplicaciones de la lista permitida. Si el agente no está funcionando, dirá que no puede ejecutar la orden.
5. Ctrl+C detiene el reconocimiento. Cerrar la ventana separada del agente detiene el acceso al dispositivo.

También se admite el arranque manual en dos terminales: `python agente_dispositivo.py` y `python sky_manos_libres.py --model modelos/vosk-model-es --execute-safe`.

## Panel Streamlit

En **Dispositivos → Voz**, el usuario puede marcar la opción de ejecución directa de acciones simples cuando existe un dispositivo emparejado y autenticado. Por defecto sigue la confirmación manual. El navegador remoto no controla Windows por sí mismo: el agente debe estar ejecutándose en el PC destinatario.

## Política de autorizaciones

- **Sin confirmación adicional, solo tras activar el modo:** abrir una web HTTPS conocida, lanzar una app de lista permitida o consultar estado.
- **Requieren confirmación por acción y permisos acotados (no incluidos en esta fase):** crear/editar/borrar archivos, envío de emails/mensajes, automatizar formularios, cambiar configuraciones e instalar aplicaciones.
- **Nunca autorizar mediante un prompt:** ejecución arbitraria de PowerShell, extracción de contraseñas/tokens, acceso a datos de terceros, eludir UAC o seguridad del sistema, control de cuentas sin inicio de sesión legítimo.

Integrar correo con OAuth y API oficial (por ejemplo Gmail); mensajería con proveedores autorizados. Una IA que redacta no demuestra que envió. Tras enviar, comprobar respuesta real del proveedor y conservar auditoría con información mínima.

### Limitaciones verificadas

La versión no incluye todavía lectura/escritura de archivos de usuario, envío de mensajes, control de móviles ni automatización de ventanas no autorizadas. El modo manos libres necesita un micrófono funcional y modelo Vosk local instalado; no se ha probado en el equipo particular del propietario.
