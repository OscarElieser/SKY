# SKY IA — P0: consulta académica extensa y aceptación física (30/10/2026)

## Alcance implementado EN CÓDIGO, pendiente de CI y prueba física

- SKY Android conserva el texto del usuario sin recortar y admite **hasta 32.000 caracteres por petición**, solo si el dispositivo está emparejado y el usuario eligió SKY API privada / SKY Automático local. Los proveedores externos mantienen su límite de 4.000 caracteres en el puente SKY API, con consentimiento independiente. El modo profundo heredado mantiene sus 16.000 caracteres de composición.
- `MobileChatRequest`, `sky_smart_router` y `sky_inference_gateway` admiten 32K de texto de usuario; Ollama puede recibir un presupuesto de hasta **4.096 tokens de respuesta** para prompts superiores a 4.000 caracteres. Una salida máxima autorizada no garantiza que el modelo use todos esos tokens ni que la respuesta sea correcta.
- El servidor controla `SKY_INFERENCE_NUM_CTX` (8.192, 16.384 por defecto, o 32.768). Para prompts superiores a 16.000 caracteres **requiere 32.768**; se rechazan solicitudes que superen una estimación conservadora del contexto. La tokenización real es específica del modelo; verificar con el modelo y no afirmar ausencia absoluta de truncado.
- `num_ctx` y `num_predict` se transmiten explícitamente al Ollama por `/api/chat`; no hay segundo proveedor, salida de herramientas, descarga de archivos, apertura de puertos ni acciones del dispositivo en este motor. El tiempo de espera para generación extensa es 190 segundos en backend y 210 segundos en móvil; los proxies reversos deberán configurarse para tolerar operaciones extensas, o implementar streaming y cancelación antes de producción.
- El transporte JSON Android mantiene un límite máximo de respuesta de 128 KiB. La aplicación conserva las reglas de HTTPS, credenciales por dispositivo, no redirecciones y autorizaciones.

**No verificado todavía:** despliegue de Ollama con pesos de un modelo real, rendimiento y RAM del servidor, solicitud real con token `chat:write` sobre HTTPS, pruebas instrumentadas Android y audio en Samsung. Los tests unitarios del protocolo usan un servidor HTTP de prueba y NO certifican un LLM real.

## Puerta P0-A: inferencia académica real, de extremo a extremo

En un servidor dedicado, con Ollama y el modelo cuya licencia fue comprobada, configurar sin exponer el puerto a Internet:

```bash
export OLLAMA_HOST=127.0.0.1:11434
export SKY_INFERENCE_WORKERS=http://127.0.0.1:11434
export SKY_INFERENCE_MODEL=qwen2.5:7b
export SKY_INFERENCE_NUM_CTX=32768
python scripts/verify_sky_local_inference.py --long-academic
```

Adaptar `SKY_INFERENCE_MODEL` al nombre exacto realmente instalado. Requisitos de aprobación: `ok=true`, `long_academic=true`, `nube=false`, al menos 500 tokens generados según Ollama, al menos 2.000 caracteres de salida, tokens de entrada informados, identificador de operación y respuesta no marcada como incompleta. Guardar hora, modelo/versión, CPU/GPU, RAM, duración, latencia y un resumen de evaluación por una persona (rigurosidad, estructura, correspondencia a las instrucciones, ausencia de fuentes inventadas). No exponer en evidencias prompts privados ni claves.

Validar además una petición móvil real `POST /api/sky/mobile-chat/chat` con token de dispositivo y por HTTPS, examinando que no se perdió un carácter del prompt, respuesta y métricas. Un test ejecutado desde el servidor comprueba **Ollama real**, pero no necesariamente confirma conectividad del teléfono hasta completar esa prueba.

## Puerta P0-B: pruebas Samsung Android 15/16

1. **Voz y audio**: activación, reconocimiento de voz del propietario sin atribuir biometría certificada, escucha autorizada en segundo plano, suspensión persistente, reproducción audible de YouTube/Spotify (distinguir Intent enviado de audio audible), permisos denegados, Doze y teléfono bloqueado. Registrar cinco intentos por orden, fallos y latencias.
2. **Archivos**: selección sin subida automática, vista previa correcta PDF, DOCX, XLSX, imagen, audio y video, permiso por archivo, procesamiento por tipo y verificación de exportación. Probar archivo grande, formatos no compatibles, interrupciones, tamaño efectivo y errores sin perder datos. Adjuntar un archivo no equivale a entenderlo.
3. **Respuesta académica**: consulta de más de 16K caracteres, estructura pedagógica, ecuaciones, pasos, citación honesta, indicador de límites e historial persistente tras cierre/reinicio.
4. **Resiliencia**: Wi-Fi/móvil, 429, 422, 503, pérdida de red, tiempos de espera, reintentos explícitos y revocación del token. No enviar contenido a nube no autorizada.
5. **Pruebas y evidencia**: commit SHA, workflows aprobados en el mismo SHA, APK firmada, SHA256, firma, versión, dispositivo, Android API, fecha, pasos, resultado observable, video/captura permitida y fallo reproducible.

## Puerta P0-C: seguridad y comercialización

Prioridad estricta: **P0-A** modelo real y ruta HTTPS autenticada → **P0-B** pruebas físicas audio/voz/archivos → **P0-C** aislamiento de cuentas, permisos, auditoría y estabilidad → pruebas reales de carga, costos, SLA y licencias. No prometer miles de usuarios, independencia total del hardware, capacidad de respuesta ilimitada ni un lanzamiento comercial hasta cerrar todas las puertas de auditoría.

Mantener una SKY con contratos compartidos. No tocar el código SKY Windows ni BAQUEANO, no borrar funcionalidades, no cambiar claves y no activar servicios cloud sin consentimiento. Los cambios de esta iteración solo deben fusionarse a `main` cuando el CI relevante esté comprobado; la firma de APK no sustituye las pruebas físicas.
