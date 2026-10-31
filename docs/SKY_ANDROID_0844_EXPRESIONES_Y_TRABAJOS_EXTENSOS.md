# SKY Android 0.8.44 — conversación natural, trabajos profesionales y control de capacidad

**Estado:** código y pruebas preparadas; falta ejecutar CI sobre el commit definitivo, publicar firma y comprobar en teléfono. No se declara un motor Ollama real ni certificación comercial.

## 1. Expresiones integradas y activación explícita

`SkyExpressionCatalog.kt` contiene **176 expresiones originales** en diez áreas: saludos (20), despedidas (18), agradecimiento (14), motivación (22), refranes (20), chistes (24), trabalenguas (16), adivinanzas (16), reflexión (14), técnicas de estudio (12).

- Se alternan respuestas por categoría en la sesión, sin recopilar datos ni invocar servicios externos.
- Ejemplos de petición: «SKY, decime un refrán», «SKY, contame un chiste», «motivame», «otro trabalenguas», «una adivinanza», «un consejo de estudio», «hasta luego».
- Las solicitudes sobre tesis, investigaciones o programación **no** se convierten en chistes ni motivación porque tengan una palabra relacionada.
- La comprobación del reconocimiento por voz no consume una expresión antes de entregar la respuesta.
- Los chistes son contenido original; se conservan acompañamiento voluntario y controles del usuario. El módulo no activa micrófono ni inventa acciones.

## 2. Entrada extensa local: 48.000 caracteres / salida máxima 6.144 tokens

`SkyPromptLengthPolicy`, `SkyOwnApiRoutingPolicy`, `metaverse/mobile_chat_api.py`, `sky_smart_router.py`, `sky_inference_gateway.py` y `SkyConversationArchive` se alinean para **preservar un prompt completo y archivarlo** bajo la ruta propia de SKY; las rutas externas siguen en 4.000 caracteres y requieren autorización. Los nuevos rangos son:

| Texto del usuario por turno | Máximo solicitado a Ollama | Condición contextual |
|---|---:|---|
| Hasta 4.000 caracteres | 2.048 tokens | Capacidad del modelo, cuenta e historial |
| De 4.001 a 32.000 caracteres | 4.096 tokens | Más de 16K caracteres requieren `SKY_INFERENCE_NUM_CTX>=32768` |
| De 32.001 a 48.000 caracteres | 6.144 tokens | Requiere `SKY_INFERENCE_NUM_CTX=65536` |

**Importante:** 48K de texto y 6.144 tokens de respuesta **no** son un contexto de 48K tokens ni garantizan redactar una tesis completa. `num_ctx` es un presupuesto del modelo con coste de memoria/latencia; entrada, historial, instrucciones y salida lo comparten. El backend estima el tamaño antes de invocar pesos, rechaza el exceso, no trunca instrucciones del usuario, no abre puertos públicos ni transfiere textos largos a otros servicios sin ruta explícita. El rendimiento se debe medir antes de habilitar 65.536 tokens de contexto en producción.

- Timeout Android chat: hasta 360 s; inferencia extensa backend: hasta 330 s. Ajustar o pasar a *streaming*, colas y cancelación para trabajos muy largos antes de comercializar.
- `SkyConversationArchive` conserva consultas completas hasta 48K y respuestas hasta 100K, evitando que el historial rechazo la salida después de un chat exitoso. Esta corrección no altera tablas ni borra conversaciones.
- `scripts/verify_sky_local_inference.py --maximal-academic` prueba sobre un modelo **Ollama real**, con un texto de 41K–48K caracteres, tokenización y respuesta medida. Requiere `SKY_INFERENCE_NUM_CTX=65536`, pesos instalados y hardware capaz. La prueba falla si faltan modelo, tokens medidos, respuesta extensa o finalización. Los tests CI con MockOllama son solo de protocolo y seguridad.

## 3. Artefacto de planificación profesional

`SkyLongWorkPlanner.kt` convierte órdenes **explícitas** en Markdown real y editable dentro del historial; el usuario puede exportar la respuesta con las herramientas de SKY existentes. Ejemplos:

- «SKY, planifica una tesis sobre inteligencia artificial educativa».
- «Prepara un plan para investigación sobre hábitos de lectura».
- «Crea un plan para proyecto de programación de una aplicación».

Produce etapas, criterios de aceptación, casillas de evidencias, validación y conservación de versiones. **No** afirma que creó una tesis, descargó referencias ni compiló una aplicación: estas acciones exigen herramientas y pruebas adicionales. No intercepta «Redacta una tesis», «Programa una app» ni otras órdenes productivas que deben ir al motor correspondiente.

## 4. Puertas P0 para alcanzar capacidad comercial

1. **LLM genuino**: Ollama en servidor autorizado, pesajes/versiones verificables, trazas de operación, tokens y latencia medidos; endpoints autenticados HTTPS, sin exposición `:11434`.
2. **Android real**: voz, audio audible, manos libres, suspensión, Doze y archivos PDF/Office/multimedia con permisos; Android 15/16 y Samsung físico.
3. **Trabajos de calidad**: investigación con bibliografía verificable, tesis por capítulos, código con tests/ejecución aislada, entregables exportados y revisiones comprobadas.
4. **Memoria y trazabilidad**: migración SQLite, privacidad, borrado/exportación, historial íntegro, permisos granulares, hash de versiones de artefactos, restauración probada.
5. **Escalabilidad**: cuentas aisladas, cola/admisión distribuida, presupuesto por persona, observabilidad p50/p95/p99, benchmarking de carga, costes y planes de contingencia.
6. **Seguridad y lanzamiento**: sin bypass de Play Protect, sin instalar APK bloqueadas, licencias de modelos y consentimiento real de usuarios. CI verde y APK firmada **no** sustituyen el piloto físico.

**No tocar** SKY Windows ni BAQUEANO en este bloque. Mantener `main` como fuente común cuando todas las verificaciones relevantes pasen, conservar historial y funcionalidades existentes.

**Límites honestos:** ninguna capacidad está "más allá del 100 %" de fiabilidad sin medición; el objetivo es eficacia verificable, tolerancia a fallos y confianza de uso.
