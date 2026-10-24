# SKY — Samsung Galaxy S23 FE AT&T → Tigo y Biblioteca Neuronal de Documentos

**Alcance:** desarrollo en rama para SKY CORE. La liberación real del operador depende de AT&T. La memoria documental es cifrada, bajo control del dueño, no entrenamiento automático del modelo.

## 1. Samsung Galaxy S23 FE (AT&T US) → chip Tigo Nicaragua

SKY puede identificar por ADB Android autorizado, explicar requisitos y acompañar el trámite oficial, pero **no dispone de un comando USB universal que quite el SIM/network lock**. No usar desbloqueos clandestinos, códigos al azar, cambios de IMEI o flasheos.

Procedimiento oficial para tu primer equipo:

1. En Samsung, **Ajustes → Acerca del teléfono → Información de software → Versión de software del proveedor de servicio**. AT&T documenta que, para Samsung anterior al 1 de septiembre de 2025, el código de proveedor terminado en `ATT/ATT` identifica una configuración originalmente de AT&T. Esto no significa automáticamente que el dispositivo ya esté desbloqueado.
2. Revisar la elegibilidad real con AT&T: teléfono normalmente comprado hace más de 60 días, completamente pagado, no reportado perdido/robado ni asociado a una cuenta con restricciones. Si se trata de **AT&T Prepaid** se aplican requisitos distintos, como servicio pagado por 12 meses.
3. Abrir el **portal oficial** https://www.att.com/deviceunlock/ (también https://www.att.com/deviceunlock/unlockstep1/ ). **No exige que el solicitante sea cliente actual de AT&T**, pero el dispositivo sí debe reunir las condiciones. Introducir el IMEI exclusivamente en el formulario oficial o en atención autorizada, **no en SKY ni en GitHub**.
4. Si el solicitante es externo a AT&T, revisar su correo y confirmar el enlace de solicitud dentro de **24 horas**. AT&T indica que algunas solicitudes se resuelven en minutos y otras pueden tardar hasta **48 horas**. https://www.att.com/support/article-modal/wireless/KM1008728/
5. Seguir las instrucciones de liberación emitidas por AT&T para ese equipo específico. Algunos teléfonos Samsung son liberados automáticamente al resultar elegibles; otros necesitan intervención guiada o código autorizado. No adivinar PIN/red ni gastar los intentos disponibles.
6. Insertar SIM física de Tigo Nicaragua; si el teléfono ya la acepta, verificar llamadas, SMS, datos y compatibilidad VoLTE del modelo y su firmware. Que aparezca `gsm.sim.state=READY` **no prueba** la liberación de red.
7. Concluir «SKY verificó funcionamiento con Tigo» únicamente cuando exista comprobación técnica adecuada. Las casillas reportadas por el dueño no son verificación independiente; el módulo devuelve por eso `sky_independently_verified_unlock: false` aun cuando el dueño marque todos los pasos.

### API creada

```http
POST /api/sky/mobile-unlock/s23fe/att-tigo
X-SKY-KEY: (token del propietario)
Content-Type: application/json
```

```json
{
  "owner_attested": true,
  "observed_state": "network_unlock_requested",
  "owner_reports_paid_off": null,
  "att_unlock_confirmation": false,
  "tigo_calls_work": false,
  "tigo_sms_work": false,
  "tigo_data_work": false
}
```

Responde con etapas, requisitos, enlace oficial y estados independientes. No acepta ni guarda el IMEI. Se mantiene `unlock_performed: false` hasta disponer de una integración que pruebe una ejecución real, y nunca se inventa ese evento.

## 2. Biblioteca de conocimiento de SKY

**Qué hace realmente:** el lector privado ya existente obtiene texto digital de PDF, DOCX, PPTX, XLSX y archivos de texto/código. Con consentimiento, el nuevo módulo `sky_knowledge_library.py`:

- Divide el texto en fragmentos y lo cifra con **Fernet**.
- Indexa palabras normalizadas usando huellas **HMAC**; no guarda términos ni fragmentos en claro dentro del archivo SQLite de la biblioteca.
- Conserva título/nombre cifrado, procedencia `owner_uploaded_unverified` y referencias por fragmento.
- Detecta duplicados por huella HMAC del contenido del archivo.
- Busca fragmentos citados de tus documentos privados y permite borrarlos.
- No reentrena pesos, no incorpora afirmaciones como verdades contrastadas, no accede a internet y no ejecuta instrucciones encontradas dentro de archivos.

Límites actuales: 200 documentos privados y máximo 60.000 caracteres de texto extraído por documento, distribuidos en fragmentos. Los archivos escaneados sin texto digital, las imágenes y los videos requieren Skills adicionales de OCR, visión o STT; **no se inventa comprensión que no ocurrió**.

### Configuración protegida

`SKY_NEURAL_MEMORY_KEY` debe contener una clave Fernet de 32 bytes en base64 de URL, guardada solo en el equipo del propietario (o en un archivo de secretos protegido mediante `SKY_NEURAL_MEMORY_KEY_FILE`). No subirla a GitHub. Sin clave, SKY responde con error en la ruta de guardado; **no degrada a almacenamiento sin cifrar**.

### API documentaria

| Método | Ruta | Función |
|---|---|---|
| GET | `/api/sky/knowledge/capabilities` | Estado y límites de biblioteca |
| POST | `/api/sky/knowledge/documents` | Subir archivo con `owner_attested=true` y `consent_to_index=true` |
| GET | `/api/sky/knowledge/documents` | Ver tus documentos |
| DELETE | `/api/sky/knowledge/documents/{id}` | Borrar documento y fragmentos |
| POST | `/api/sky/knowledge/search` | Buscar por palabras con citas |

La ruta anterior `POST /api/chat/upload` ahora acepta los campos multipart opcionales `remember_document=true` y `owner_attested=true`. En el chat, el control visible **«Guardar documentos»** envía esas opciones para documentos admitidos. Por defecto está desactivado. Las respuestas informan `doc_id` y `knowledge_index_status` para indicar **si se guardó de verdad**.

Ejemplo de búsqueda:

```json
{"query":"aprendizaje colaborativo","limit":5}
```

El usuario puede decir o escribir:

> «SKY, buscá en mis documentos sobre aprendizaje colaborativo».

SKY devuelve hasta cuatro fragmentos identificados por nombre y referencia `sky-doc:<id>:chunk-<n>`, sin presentarlos como información externa verificada.

## 3. Qué falta para un SKY profesional integral

Esta entrega **no** completa automáticamente todas las funciones de otras IA. Para avanzar hay que integrar un generador de respuestas RAG con citas y pruebas contra inyección de prompts, extracción OCR y análisis de imágenes/videos, evaluación de fuentes web, creación y validación de documentos profesionales y pruebas físicas de control Windows.

Requisitos de liberación de esta rama:

- GitHub Actions Windows y Linux del **último commit** exitosos.
- Prueba local de interfaz y del servicio SKY.
- Un Samsung Galaxy S23 FE propio conectado por USB, con depuración autorizada, sin prometer desbloqueo de AT&T.
- Prueba de indexar/buscar/eliminar documento de forma cifrada, confirmando que la opción de memoria se respetó.
- `main` intacto hasta revisar también las dependencias de PR #9–#13.

Esta rama es una propuesta técnica, no una instalación concluida en el PC del dueño.
