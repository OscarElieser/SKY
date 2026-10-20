# Historial técnico: SKY v9.6 · Contextual Coordination

## Nuevas capacidades verificadas

- Detección local ampliada de intenciones de creación, con manejo de tildes y distinción de preguntas.
- Contexto acotado al proyecto existente: objetivo y títulos de entregables anteriores. No hay búsqueda secreta ni transferencia a IA externa.
- Borradores de documentos más organizados: objetivo, destinatarios, ejes, continuidad, entregables y validaciones pendientes.
- CSV explícito dentro del chat para crear Excel, con rechazo cuando faltan filas o encabezados.
- **Edición del plan pendiente** mediante endpoint autenticado; huella de aprobación invalidada al modificar condiciones.
- **Revisión autorizada de entregables** Word/PowerPoint/PDF, diseños HTML y mundos procedurales: nueva versión enlazada al proyecto y original conservado.
- Vista del plan con referencias de dependencia entre etapas y revisiones del proyecto en la conversación.
- `intelligent_revisions` como tabla nueva compatible con la base v9.5.
- Diagnóstico e información de plataforma versionados a 9.6.0.

## No implementado / límites reales

- Edición semántica exhaustiva ni actualización automática de Word dentro de la misma versión; se crea una versión nueva.
- Revisión desde chat de fórmulas de un XLSX existente: usar Office Studio.
- Toma de decisiones financieras y cambios de producción sin autorización.
- Reentrenamiento de modelos neuronales, realidad virtual fotorrealista y despliegue público masivo.

## Compatibilidad

Sin pérdida intencional de módulos de v9.5, rutas existentes, archivos o bases privadas. Pruebas de regresión: 154/154; pruebas nuevas: 8/8.
