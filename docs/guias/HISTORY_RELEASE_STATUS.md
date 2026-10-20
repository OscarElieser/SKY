# SKY IA — estado verificable de publicación histórica

Dirección del proyecto: **Oscar Elieser Chamorro Guzmán**.

Verificado el 19 de octubre de 2026.

## Código fuente conservado en ramas

- `versions/v9.8` — commit `404dbbea139ddc3363d36159d329d21d836486d9`
- `versions/v9.9` — commit `efe59f4abcf641a6fa92b31b893972268518b876`
- `versions/v10.0` — commit `b83e20d571d03b4a100a7384c7743382b5862cb2`
- `versions/v10.1` — commit `33c61b11874cd877dd45a7e7924962498da1b09e`
- `versions/v10.2` — commit `41b85d3a366b129b6efe340b94aef7c5d084c0cf`
- `versions/v10.3` — commit `15a6b2a77a5d3e1bb12435373e1b0878972ded26`

Estas ramas identifican **snapshots de código**; no equivalen a adjuntar un ZIP histórico de cada versión.

## ZIP históricos

El inventario `HISTORIAL_VERSIONES.json` registra **22 archivos originales**, con sus nombres, tamaños y SHA-256. A fecha de esta verificación, solamente dos ZIP se encuentran efectivamente almacenados bajo `history/archives/` en GitHub:

- `NeuralT_Personal_MLP_GRU_Engine_Sensor.zip`
- `NeuralT_Universal_JARVIS_v4_2_Gemini_Baqueano_Voz_Dispositivos.zip`

**20 ZIP pendientes de subir como adjuntos a GitHub Releases.** El repositorio tiene cero Releases publicados a la fecha de verificación. No declarar completada su publicación hasta inspeccionar la página de Releases y verificar los 22 assets correspondientes.

## Para completar la publicación

1. Descargar y extraer `SKY_IA_HISTORIAL_VERSIONES_COMPLETO.zip` entregado en la conversación.
2. Instalar y autenticar GitHub CLI (`gh auth login`) con acceso a `OscarElieser/SKY`.
3. Revisar cada ZIP histórico antes de publicarlo, por privacidad y licencias; el SHA-256 verifica integridad, no seguridad.
4. Desde la raíz del código de SKY v10.3 ejecutar: `bash scripts/publish_history_gh.sh /ruta/a/carpeta_extraida`.
5. Comprobar los Releases y sus adjuntos en `https://github.com/OscarElieser/SKY/releases`.

El proceso de publicación evita sobrescribir `main` y comprueba integridad de los ZIP. No se exponen secretos ni datos de producción por defecto, pero debe auditarse el contenido histórico antes de compartir archivos.
