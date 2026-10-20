# Validación reproducible — SKY IA v10.5

**Visión y dirección conceptual:** Oscar Elieser Chamorro Guzmán.

## Resultados locales del 19 de octubre de 2026

- `PYTHONPATH=. pytest -q --disable-warnings`: **224 pruebas superadas** (214 heredadas de v10.4 + 10 adicionales de v10.5). Ejecución de ~35 segundos en este entorno.
- `PYTHONPATH=. pytest -q tests/test_sky_v10_5_global.py`: **10 pruebas superadas**.
- `node --check metaverse/static/creative.js`: sintaxis correcta.
- `python scripts/security_audit_v103.py .`: **303 archivos revisados; 0 coincidencias detectadas** por las reglas del escáner. Esto **no** equivale a un pentest ni una auditoría externa.

## Pruebas nuevas

1. Respaldo cifrado con SQLite y recurso PNG, autenticidad, hash y restauración real en una carpeta nueva.
2. Detección de sobrescritura, clave errónea y modificaciones en archivo cifrado.
3. Restricciones de medios, nombres de colecciones y enlaces simbólicos.
4. Rechazo de rutas `../` dentro de un ZIP aunque haya sido cifrado con una clave válida.
5. Prohibición de restaurar dentro de la instalación activa.
6. Traducciones revisadas en ocho idiomas y escrituras diferentes.
7. Negativa explícita al uso de un reconocedor de voz no instalado.
8. Conversión local de WAV PCM a 16 kHz mediante FFmpeg, más validación de formatos/tamaño.
9. Autenticación exigida en las rutas HTTP privadas de transcripción y capacidades.
10. Rechazo de grabaciones mayores de 60 segundos, sin truncar silenciosamente.

## Traducción: cobertura observable y no inflada

La auditoría de etiquetas visibles estáticas detectó 547 etiquetas tras añadir controles de STT (antes había 541). Las etiquetas traducidas ahora incluyen: portugués 76, francés 76, árabe 71, chino 69, japonés 69 y suajili 56. Inglés conserva 113. Estas cifras **no** son porcentajes completos de traducción funcional del producto: se excluyen mensajes generados, documentos y contenidos del usuario.

## Limitaciones de validación

- No se instaló ni se utilizó un modelo Whisper local en este entorno. **No se ha probado una transcripción real**, solo preparación de audio, configuración requerida y protecciones.
- No hay auditoría externa ni despliegue público de producción.
- La restauración cubre SQLite y medios de la biblioteca privada de Creative Studio; no reemplaza una estrategia integral para todos los archivos, secretos y servidores.
- Los límites de carga y tiempo de STT protegen esta API local; una instalación pública requiere aislamiento y cuotas distribuidas adicionales.
- BAQUEANO no se modificó.
