# Validación técnica SKY v9.4

- **Código:** `python -m pytest -q` → 146 aprobadas.
- **Frontend:** `node --check metaverse/static/sky-flows.js` → sin errores sintácticos.
- **Servidor:** Uvicorn sirviendo HTTP local real; endpoints privados con `X-SKY-KEY` válidos y rechazo 401 de clave incorrecta.
- **Aprobación:** previsualización con huella SHA-256 y rechazo 409 al aprobar una huella diferente.
- **Autonomía supervisada:** proyecto asociado a un flujo real de 4 pasos (`plan → world → document → experience`); 4 pasos completados, pausa y reanudación antes de los pasos finales.
- **Persistencia y exportación:** ZIP real con manifiesto, archivo `.docx`, diseño HTML, especificación y mundo `.glb`; integridad ZIP revisada. Véase `ejemplos/sky_v9_4/validacion_http_real.json`.
- **Contexto congelado:** la edición posterior del nombre de un proyecto no modifica los documentos de un flujo previamente definido; comprobado con DOCX creado y leído.
- **Migración:** prueba de creación de tabla con esquema antiguo y adición de columnas nuevas, `PRAGMA integrity_check == ok`.
- **Privacidad:** rutas de flujos, resúmenes de proyectos y BAQUEANO solo con clave del propietario; una contraseña incorrecta se rechaza.
- **Limitaciones:** Chromium está instalado, pero la política del entorno bloquea `http://127.0.0.1` y el dominio de prueba; **no hubo validación visual del navegador**. Sin pruebas de proveedores IA externos, voz física, VR, concurrencia masiva ni disponibilidad 24/7.

Conclusión: **funcionalidad local verificada para el alcance indicado**, no certificación de producción pública.
