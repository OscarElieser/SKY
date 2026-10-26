# SKY · Control real de aplicaciones y documentos — 26/10/2026

## Objetivo del propietario
SKY debe ejecutar instrucciones por voz o texto directamente dentro de Word, Excel,
PowerPoint, editores, navegador y aplicaciones autorizadas, como lo haría el
propietario, pero con permisos, trazabilidad y prueba de resultados. Conservar
toda la API, HUD, voz, cerebro, capacidades, historial y módulos existentes.

## Auditoría y primera capacidad entregada en PR #52
El agente original `type_text` empleaba el portapapeles y enviaba Ctrl+V a la
ventana activa, sin verificar que era Word; no se sustituye ni se proclama
seguro para documentos. El sistema de documentos registraba tareas `PENDING`
sin demostrar necesariamente la creación de archivos.

Se añadió `neural_core/sky_word_editor.py`, llamado por
`sky_asistente_personal.interpretar()/reglas()`, con una nueva acción
`word_write` bajo la capacidad **existente** `type_text`:
- El dueño dice **«SKY, escribí en Word: Hola Nicaragua»** y ve una propuesta
  de escritura. La misma ruta sirve para voz y texto.
- SKY requiere una **confirmación individual** para toda escritura;
  `--auto type_text` no permite saltarla en el HUD.
- El agente Windows valida parámetros, exige política local y respeta la
  parada de emergencia; audit ledger no guarda el cuerpo dictado.
- Microsoft Word debe estar abierto y visible, con **exactamente un documento**
  editable (no protegido, no solo lectura).
- Se usa Word COM (pywin32) para insertar texto al final del documento
  sin tocar el portapapeles ni simular Ctrl+V sobre Chrome.
- SKY relee `doc.Content.Text` y solo informa `VERIFIED` si verifica la
  inserción. No ordena guardar automáticamente ni afirma estado de AutoSave.
- Nunca reemplaza contenido existente, abre archivos arbitrarios, guarda
  archivos ni sobrescribe el disco mediante esta acción.
- El editor se carga bajo demanda, sin cargar Word ni otro modelo al arrancar.

## Evidencia / limitaciones
- Existen pruebas unitarias sintéticas del parseo, privilegios, escritura
  en documento falso, rechazo de documentos ambiguos/protegidos y
  preservación de modificaciones del propietario.
- La ejecución física en la computadora del propietario y la compatibilidad
  Word/COM **no se han verificado aún**; ni siquiera un resultado CI de la
  última revisión se debe considerar certificado sin consultarlo.
- El editor no investiga por sí mismo ni produce automáticamente un informe
  completo desde fuentes. No puede declararse producto final.
- `type_text` legado sigue siendo un riesgo de foco/portapapeles para
  aplicaciones distintas de Word; requiere auditoría antes de emplearlo.
- Con Word AutoSave activado, Word puede persistir cambios sin que SKY llame
  Guardar. Solo trabajar con documento descartable hasta completar pruebas.

## Aceptación física antes de fusionar
1. Instalar con `scripts/sky_pr52_word_editor_install.py` en modo
   comprobación, y luego `--aplicar` tras detener API/agente; guardar copia.
2. Ejecutar test suites `test_sky_word_editor.py` y
   `test_sky_pr52_word_editor_install.py`; sin errores, no ejecutar pruebas
   destructivas.
3. Confirmar `import pythoncom, win32com.client` desde `.venv`.
4. Una única ventana de Word con documento nuevo y descartable.
5. SKY muestra `word_write` y solicita confirmación.
6. Verificar que agrega texto al final, no en Chrome, sin modificar el
   portapapeles, y que informa `VERIFIED` tras leer Word.
7. Confirmar que 0 / 2 documentos, lectura sola, bloqueo de política y
   parada de emergencia impiden ejecución.
8. Comprobar que API, voz, HUD, plugins, modelos y funcionalidades previas
   siguen trabajando. Revisar conflictos del PR #52 y CI antes de `main`.

## Secuencia de desarrollo restante
- **Investigación verificable → redacción → revisión → Word**: usar conectores
  de búsqueda existentes con enlaces y fechas reales, sin inventar fuentes,
  y pasar texto por la misma acción confirmada. El agente debe presentar el
  borrador/plan antes de tocar un documento real.
- **Documentos formales**: estilos de Word, títulos, secciones, tablas,
  citas y bibliografía; guardado controlado en carpeta autorizada con
  nombre sin colisiones y verificación de archivo abierto.
- **Excel / PowerPoint**: adaptadores nativos específicos con selección
  de archivo y celda/diapositiva, preview y lectura de resultado.
- **Navegadores y aplicaciones web**: navegación con Playwright u otros
  conectores autorizados; cuidado de sesiones, cuentas y datos privados.
- **Otras aplicaciones**: agente de escritorio con modelo de foco
  robusto, operaciones permitidas, captura de pantalla, detección de errores
  y compensación/reversión cuando proceda; no habilitar RPA ciega.
- Métricas: tiempo de interpretación, permiso, acción y verificación;
  éxito real y motivos de fallos, sin datos sensibles en registros.
