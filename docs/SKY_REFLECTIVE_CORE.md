# SKY: bucle reflexivo y recuperación de experiencias

## Tres capas sin sustituir el núcleo existente

1. **Percepción y contexto:** `sky_cognition` clasifica la intención, el riesgo y el contexto consentido.
2. **Razonamiento y ejecución controlada:** `sky_skill_builder.proponer` genera una habilidad; `validar_codigo` comprueba su estructura y `probar` la pasa por `sky_sandbox_runner`. Se permiten uno a tres intentos de generación y la repetición exacta de código detiene el bucle.
3. **Reflexión y memoria:** `sky_reflective_core` convierte cada reporte de prueba en una etiqueta segura, guarda evidencia local y recupera lecciones para el siguiente intento. El feedback al generador nunca contiene el texto de las pruebas ni stack traces.

**Flujo:** pedido → recuperación de lecciones → propuesta → revisión estática → pruebas aisladas → diagnóstico → corrección limitada → revisión del propietario.

`sky_skill_builder.aprobar` **sigue requiriendo autorización del dueño y una nueva prueba**; ninguno de los nuevos componentes instala código, ejecuta acciones Android o Windows ni concede permisos.

## Memoria y alcance verificable

- SQLite local: `local_data/sky_reflective.sqlite3`, configurable con `SKY_REFLECTIVE_DB`.
- Columnas: categoría general, tipo de fallo, resultado de las pruebas, vector de hashing determinista de 32 componentes y fecha. **No** almacena prompts, entradas de pruebas, código, rutas, secretos ni errores brutos.
- Retención: 90 días y máximo 1.500 registros. Recuperación consultiva de hasta dos lecciones por tarea.
- Estos vectores **no son embeddings semánticos entrenados**; la memoria es una base de recuperación por características. Los embeddings semánticos locales cifrados y un almacén vectorial especializado quedan como fase futura.
- El éxito es evidencia de *tests*, **no** prueba física de acción ni reentrenamiento del modelo. No hay consciencia en sentido humano ni actualización de pesos.
- El runner Python existente no es un sandbox de seguridad equivalente a una VM o contenedor endurecido. Código no confiable exige aislamiento de sistema operativo antes de elevar privilegios.
- Este bloque es compatible con el código Android y Windows sin alterar sus permisos, contratos ni interfaces. No constituye despliegue a APK.

## Pruebas

```bash
python -m pytest tests/test_sky_reflective_core.py -q
python -m pytest tests/test_sky_v12_4_habilidades.py -q
```

Las pruebas verifican privacidad, reintentos limitados, recuperación categórica y que ninguna propuesta fallida se instale automáticamente. Una prueba real de dispositivo Android y Windows continúa siendo requisito separado.
