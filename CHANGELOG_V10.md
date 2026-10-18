# SKY IA v10.0 — Creative Intelligence

**Dirección del proyecto:** Oscar Elieser Chamorro Guzmán.

## Implementado y verificado

- Seguimiento local de una región visual en MP4 con OpenCV (`TM_CCOEFF_NORMED`) mediante cuadros de selección definidos por el usuario. El motor entrega una secuencia editable de posiciones y confianza por muestra; limita el seguimiento a 20 segundos y 100 puntos.
- Capas gráficas adicionales en video con posición, tamaño, transparencia, rangos temporales y trayectoria de fotogramas clave. Exportación de MP4 por FFmpeg, reutilizando el mismo render de SKY.
- Previsualización exacta desde un fotograma del último MP4 exportado **de la versión actual**; avisa si la edición aún no está renderizada.
- Edición por lenguaje natural acotado: modificar posición u opacidad de una capa del clip, con historial de versiones y aprobación del propietario mediante la API privada.
- Reutilización de medios y trayectorias en `.skyzip` sin modificar los archivos originales.
- Prueba de conectividad Gemini real **bajo solicitud explícita**, sin guardar ni mostrar la clave. La llamada real sigue pendiente de credenciales privadas en este entorno.
- Interfaz del estudio plegable dentro de SKY; la portada principal no añade accesos innecesarios y BAQUEANO sigue restringido al creador.

## Límites y honestidad técnica

- No existe todavía seguimiento semántico de objetos ni seguimiento estable ante todas las oclusiones. La coincidencia de plantillas puede equivocarse cuando la apariencia cambia. Revisar el resultado.
- Las capas de video compuestas admiten imágenes y PNG alfa; no son todavía una línea de tiempo multipista libre equivalente a Premiere.
- La vista previa corresponde al último video realmente renderizado, no a modificaciones que estén solo en memoria.
- No se realizaron pruebas de Gemini reales sin una clave API válida, ni pruebas VR o despliegue de gran escala.

## Comprobación

`PYTHONPATH=. pytest -q` — 185 pruebas exitosas (183 heredadas + 2 nuevas de seguimiento/composición/autorización).

## Publicación

Los cambios deben verificarse en la rama main del repositorio `OscarElieser/SKY` mediante comparación del código y pruebas; un ZIP local por sí solo no demuestra que GitHub haya recibido los cambios.
