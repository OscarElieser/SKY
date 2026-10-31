# SKY API propia — arquitectura de inferencia y preparación comercial

**Estado: desarrollo incremental — no aprobada para venta masiva.** Esta guía no declara desplegados servicios, hardware, inferencia en Android, facturación, autoscaling ni disponibilidad 24/7. Actualizada el 30 de octubre de 2026.

## 1. Lo que está conectado mediante código

- **Android**: `SkyOwnApiRoutingPolicy` controla el consentimiento de «Priorizar mi SKY API privada». Requiere URL HTTPS válida, chat emparejado y token específico cifrado con Android Keystore. Envía a `/api/sky/mobile-chat/chat` con `proveedor="ollama"`, `autorizar_nube=false`, `autorizar_datos_privados=false`. No abre un puerto Ollama ni ejecuta modelos dentro del teléfono.
- **Servidor**: `metaverse/mobile_chat_api.py` verifica el token limitado y su límite por ventana antes de llamar a `metaverse/sky_home_api.py`. Esta consulta pide exclusivamente el proveedor Ollama; el modelo debe estar cargado en el servidor. Si falla, **no** se cambia silenciosamente a proveedores con cuota. La consulta permanece en el editor Android para reintentar.
- **Comprobación real**: `POST /api/sky/mobile-chat/status` requiere token de chat válido, devuelve `local_ollama_ready` basado en el catálogo del Ollama de loopback. «Disponible» no significa que haya generado una respuesta, que tenga rendimiento suficiente ni que tenga acceso desde Internet; estas tres pruebas requieren evidencia adicional.
- **Límite de texto actual**: 4.000 caracteres por solicitud a la ruta SKY Home. Nunca recortar silenciosamente el prompt para encajarlo. Los controles de cuota, acceso y tiempo de espera permanecen activos.
- **Windows**: el flujo Android solo añade componentes opcionales y una ruta auxiliar de estado al servidor; no altera la aplicación Windows ni los modelos que ya usa.

## 2. Seguridad obligatoria

1. **No publicar** `http://<IP>:11434`, `OLLAMA_HOST=0.0.0.0` ni un túnel público al servicio Ollama sin autenticación. El servidor de inferencia debe escuchar en loopback o una red interna realmente aislada.
2. Entrada pública únicamente por API Gateway HTTPS con autenticación individual, autorización por alcance, límites por cliente, controles antiabuso y trazabilidad de errores. Las credenciales de proveedores y las maestras permanecen en infraestructura controlada y nunca en APK, Git o logs.
3. Solicitudes sin acciones del sistema. Cualquier herramienta que modifique archivos, redes sociales, compras, llamadas o ajustes debe pasar por otro permiso granular supervisado, con evidencia y políticas de denegación.
4. Aislamiento por empresa/usuario (multitenancy) para memoria, documentos, historiales y claves. En el servicio actual el emparejamiento está orientado al propietario y NO reemplaza la identidad comercial de usuarios.
5. Métricas agregadas sin conservar textos completos por defecto: ID de operación, duración, cantidad de tokens, ocupación de GPU, uso por cliente, fallos, motivo del fallback y costos. Respetar periodos de retención y derecho de eliminación.

## 3. Próxima capa comercial: SKY Inference Gateway

Propuesta **no implementada**:
- Autenticación y cuentas de clientes (planes y dispositivos), registro de consentimientos, revocación, cuotas por plan y presupuesto de tokens.
- Router de capacidad: local Android **solo si existe un motor nativo instalado y probado** → SKY API propia con GPU → proveedores externos solamente autorizados. Rutas de navegación web/citas con herramientas verificadas; nunca presentar un LLM offline como fuente actualizada.
- Pool de workers Ollama/vLLM/llama.cpp con GPU apropiada y límites de concurrencia, almacenamiento de modelos auditados, colas de solicitudes, timeout, circuit breaker, réplicas y pruebas de carga.
- Observabilidad: disponibilidad, tasa de error, latencia p50/p95/p99, tokens/s, costo por 1.000 tokens, retardo de cola, éxito y cancelación. Definir SLO solo tras medir infraestructura real.
- Modelo de negocio: presupuesto por cliente y cobro transparente; los modelos de pesos abiertos no eliminan el costo de energía, servidores, ancho de banda, soporte o licencias.

## 4. Inferencia genuinamente en Android — segunda fase

- Candidato: SDK **LiteRT-LM** de Google AI Edge, o variante `llama.cpp` con binding Android/JNI y GGUF. Debe usarse una dependencia fijada a una versión probada, no un ejemplo ficticio.
- Instalar el modelo por descarga autorizada dentro del almacenamiento privado de la app, con URL permitida, tamaño declarado, SHA-256, licencia aceptada, descarga reanudable y eliminación controlada. **No** meter pesos de gigabytes obligatoriamente en la APK.
- Pruebas en el Samsung: memoria libre real, carga del modelo, tokens por segundo, temperatura, consumo de batería, estabilidad después de varios turnos, funcionamiento offline sin claves ni red, manejo de poco espacio y apagado seguro. No asumir aceleración NPU/GPU sin verificación.
- Comprobar condiciones comerciales de **cada modelo** y de sus componentes (licencias, restricciones, atribución y redistribución) antes de incluir pesos en la app o vender inferencia alojada.
- **Estado actual: sin runtime LiteRT-LM/llama.cpp integrado, sin pesos descargados y sin prueba local en Samsung.**

## 5. Criterios de aceptación

- [ ] El propietario autoriza SKY API en la app; sin autorización no se envía al servidor.
- [ ] El móvil comprueba token y modelo por HTTPS; un token revocado no puede ver el estado.
- [ ] Un modelo Ollama auténtico procesa una consulta de texto sin llamadas a Gemini ni Groq; registrar ID, latencia y evidencia, sin almacenar secretos.
- [ ] Modelo desactivado → error veraz y borrador conservado, sin fallback automático.
- [ ] Petición de información actual → herramienta de fuentes verificadas, no modelo offline presentado como fuente.
- [ ] Pruebas de compilación firmada Android, unitarias y emuladores API 35/36 aprobadas.
- [ ] Despliegue comercial con usuarios independientes, cotas, protección contra fugas y carga de concurrencia evaluado.

## 6. Estado de la versión

Los cambios son fuente en `main`. La disponibilidad de una APK se verifica exclusivamente mediante [GitHub Actions](https://github.com/OscarElieser/SKY/actions) y [Releases](https://github.com/OscarElieser/SKY/releases). No afirmar que está terminada una integración cuando falten configuración del servidor y prueba de solicitud real.

Referencias técnicas: [LiteRT-LM Android](https://developers.google.com/edge/litert-lm/android), [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api/introduction.mdx), [Ollama Authentication](https://github.com/ollama/ollama/blob/main/docs/api/authentication.mdx), [Condiciones Gemma](https://ai.google.dev/gemma/terms/).
