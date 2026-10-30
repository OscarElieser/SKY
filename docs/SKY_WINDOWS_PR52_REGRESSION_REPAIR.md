# SKY Windows — resolución controlada de regresiones PR52

Este bloque corrige una regresión de compatibilidad real y alinea las pruebas con contratos ya exigidos por SKY. No modifica interfaces Android ni altera la ejecución de órdenes.

## Protección del supervisor
- Si la API de SKY ya está activa, un nuevo inicio **no** debe crear otro supervisor ni duplicar la escucha. Libera el candado temporal y conserva el proceso anterior.
- Si un servicio ajeno ocupa el puerto del agente, evita empezar sobre ese servicio; **no** lo finaliza ni lo sustituye.
- `--status` sigue siendo el mecanismo de diagnóstico, sin forzar cierre de procesos.
- Estos cambios no habilitan controles de dispositivo adicionales ni debilitan la autenticación.

## Reparadores legacy y archivos del dueño
- El actualizador de noticias comprueba el punto exacto de inserción con saltos de línea normalizados, pero conserva CRLF cuando el archivo original lo utiliza; el resultado es idempotente.
- La prueba del reparador de voz incluye ahora el método `record_turn` que la propia reparación exige, y mantiene un ensayo de rechazo cuando está ausente.
- La prueba del atajo Ctrl+F4 contiene ahora una función con cláusulas completas, para que la verificación de sintaxis compruebe la inserción verdadera en vez de un ejemplo truncado.
- En el producto, los instaladores siguen siendo de **solo comprobación por defecto**; requieren `--aplicar` y realizan respaldos antes de cambiar archivos.

## Evidencia necesaria
Se debe superar `SKY PR52 Windows validation` en GitHub Actions y registrar cualquier otra regresión en la incidencia #92 antes de fusionar a `main`. Las pruebas automáticas no equivalen a una validación física de voz, micrófono, apertura de Word o atajos en el PC del propietario.
