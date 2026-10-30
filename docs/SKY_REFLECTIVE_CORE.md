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
- La recuperación por defecto utiliza vectores de características de 32 dimensiones, **no** embeddings entrenados.
- **Modo semántico local opcional**: con `SKY_REFLECTIVE_SEMANTIC=1` y el modelo de Ollama `nomic-embed-text` instalado, `sky_reflective_embeddings.py` obtiene embeddings reales de **descripciones fijas de categorías**. Nunca transmite el pedido completo, secretos, documentos ni errores al modelo; las similitudes amplían la búsqueda entre categorías. Si Ollama no está disponible, se recupera automáticamente el método determinista.
- La recuperación semántica de *experiencias completas* con embeddings de cada proyecto y sincronización cifrada Windows–Android **no están implementadas**. Tampoco se almacena un vector de texto sensible.
- El éxito es evidencia de *tests*, **no** prueba física de acción ni reentrenamiento del modelo. No hay consciencia en sentido humano ni actualización de pesos.
- El runner Python existente no es un sandbox de seguridad equivalente a una VM o contenedor endurecido. Código no confiable exige aislamiento de sistema operativo antes de elevar privilegios.
- Este bloque es compatible con el código Android y Windows sin alterar sus permisos, contratos ni interfaces. No constituye despliegue a APK.

## Activación opcional (Windows / servidor Python de SKY)

```powershell
ollama pull nomic-embed-text
$env:SKY_REFLECTIVE_SEMANTIC="1"
$env:SKY_REFLECTIVE_EMBED_MODEL="nomic-embed-text"
```

El endpoint predeterminado es `http://127.0.0.1:11434`. El sistema rechaza direcciones de red externas y redirecciones. Las descripciones enviadas son categorías públicas declaradas dentro del código. Esta configuración no instala ni inicia por sí sola Ollama.

Métricas de evidencia mediante `sky_reflective_core.report()`: categorías, pruebas superadas/fallidas y tasa de acierto de pruebas. No equiparar esas estadísticas con éxito en dispositivos físicos.

## Pruebas

```bash
python -m pytest tests/test_sky_reflective_core.py -q
python -m pytest tests/test_sky_v12_4_habilidades.py -q
```

Las pruebas verifican privacidad, reintentos limitados, recuperación categórica y que ninguna propuesta fallida se instale automáticamente. Una prueba real de dispositivo Android y Windows continúa siendo requisito separado.
