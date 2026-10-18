# SKY IA v9.5 — Registro de cambios

## Incluido

- Nuevo `sky_intelligent.py`: solicitudes persistentes, plan de trabajo, huella de aprobación, conversión a proyecto + flujo existente, lectura de avance y entregables.
- Nuevo `intelligent_api.py`: una ruta de conversación que decide si devuelve respuesta o propuesta y cuatro rutas para preparar, consultar, autorizar y recuperar trabajos.
- Pantalla principal simplificada conservada: las herramientas se activan en segundo plano; la propuesta y el progreso se muestran únicamente cuando hay un trabajo activo.
- Descargas autenticadas de documentos, HTML y ZIP sin exponer la clave en URLs; continuidad con el proyecto seleccionado.
- Nuevas pruebas de seguridad, aprobación, recuperación, exportación y continuidad. Total: **154 pruebas exitosas**, 146 heredadas y 8 nuevas.
- Integrado en SKY Integration Center y respaldo extendido de SQLite.

## Fuera de alcance en esta versión

- Planificación generativa general mediante un modelo de lenguaje para cualquier solicitud; el plan local usa reglas deterministas revisables.
- Creación de contenidos fotorrealistas complejos, Excel sin datos aportados, publicación automática, pagos, acceso a BAQUEANO en producción.
- Servicio en segundo plano permanente con la computadora apagada o sin servidor.
- Carga multiusuario masiva o infraestructura pública certificada.
