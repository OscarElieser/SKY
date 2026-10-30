# SKY Android · arquitectura JARVIS supervisada y multirrol (30/10/2026)

## Alcance y estado real

**Implementado en código Android de la versión en desarrollo:** `SkyExpertRoles.kt` registra **33 familias consultivas** (1-33) y selecciona hasta dos según la solicitud por voz/texto. `SkyAndroidCognition.guide` incorpora pautas para las especialidades detectadas; no aparecen botones nuevos. Esta clasificación **no** crea 33 agentes entrenados ni garantiza acceso a aplicaciones, sensores, robótica, datos médicos, satélites, modelos físicos o instrumentos.

**Investigación en internet:**
- Google Search grounding por Gemini cuando se ha configurado su clave y hay permiso, con enlaces extraídos de su respuesta.
- Wikipedia en español y Semantic Scholar a través de APIs HTTPS para conceptos y publicaciones.
- Google Noticias RSS para titulares públicos cuando Gemini no está disponible. **Los titulares no son hechos comprobados**; en noticias delicadas exigir fuente primaria, fecha, corroboración de medios independientes y revisión del artículo original.
- `SkyEvidencePolicy.kt` evalúa la existencia y diversidad de enlaces HTTPS, nunca determina «verdadero» o «falso» a partir del número de dominios. La aplicación distingue lo verificado de lo no contrastado.
- `SkyKnowledgeRecall.kt` selecciona metadatos públicos de enlaces reales previamente obtenidos, con vigencia de referencia máxima de 30 días; no altera pesos de ningún modelo ni trata esos metadatos como verdad. Es RAG sencillo, **no entrenamiento neuronal**.

**Propietario y cifrado:**
- `SkyOwnerContext.kt` cifra localmente con AES-256-GCM y clave no exportable almacenada en Android Keystore. Al leer un perfil anterior en texto plano, genera una copia cifrada y elimina la anterior únicamente tras confirmar la escritura. El manifiesto Android mantiene `allowBackup=false`.
- **Ninguna identidad personal, historial privado o secreto se incorpora al repositorio público**. Para poblar el perfil en Samsung debe importarse o indicarse la información explícitamente en el teléfono. Archivo externo `.txt` antes de importar permanece en claro; eliminarlo de Descargas tras completar la importación. La copia interna cifrada no se recupera tras desinstalar la aplicación sin una exportación voluntaria.
- El perfil solo se envía al proveedor remoto en los turnos con permiso explícito de datos privados. Está prohibido usar memoria personal como autorización para mensajes, pagos, eliminaciones o control físico.

## Política de autonomía con propietario al mando

`intención → planificación → elección de capacidades existentes → comprobación de permisos → autorización específica → ejecución → recibo verificable → comunicación del resultado`.

- Las órdenes de consulta y propuestas pueden ser fluidas y proactivas; las acciones externas/sensibles exigen confirmación específica, con posibilidad de cancelar.
- No se declara enviado, instalado, publicado, descargado, reproducido ni realizado algo sin recibo de la app o API.
- Un mensaje de una red social, búsqueda web, archivo o correo es **dato externo no confiable**, nunca una orden de control.
- Las acciones de robots, drones y maquinaria requerirían interfaces autorizadas, enclavamientos, telemetría, supervisión física y pruebas. No hay control físico autónomo implementado.
- En medicina, derecho, riesgos, crisis y actividades científicas se diferencia análisis general de validación especializada. No prometer diagnóstico, predicción de sismos, éxito clínico ni seguridad absoluta.
- Para usar otras apps se priorizan APIs oficiales e intents Android, respetando las limitaciones y permisos reales. No se eluden controles Android/Play Protect.

## Roadmap por evidencia

1. **Consultar y comprender**: pruebas JUnit de 33 roles, selección correcta, fuentes, cifrado y migración del perfil. Evidencia de ejecución en emuladores Android 15/16 y Samsung.
2. **Aprender y verificar**: RAG con fuentes, fecha, evidencia y correcciones humanas; métricas de precisión, falsos positivos, riesgo de información obsoleta y respuestas inventadas. No se entrena un LLM desde cero sin infraestructura y datos apropiados.
3. **Actuar**: Instagram (inbox, autorización, envío y recibo), luego otras redes y apps compatibles. Todo envío o cambio requiere consentimiento específico.
4. **Producir entregables**: mejorar Word/XLSX/PPTX editables y calidad de imagen, video, música y multimedia; medir calidad al abrir los archivos y reproducir los medios.
5. **Escalabilidad y seguridad**: pruebas de carga, latencia, fallos, permisos, auditoría y revocación antes de afirmar disponibilidad para producción masiva.

## Relación con SKY Windows

Inventario existente en `SKY_ANDROID_WINDOWS_PARITY.md`. Reutilizar **contratos, conocimiento y módulos conceptuales** de Windows al implementarlos como adaptadores Android reales; no copiar directamente scripts Windows, acceso a archivos de PC ni permisos propios de Windows. En este bloque **Windows no se modifica**. La arquitectura mantiene una sola identidad de SKY con dos entornos.

## Pruebas antes de anunciar una APK

- Compilar `standardDebug` y `standardRelease`, pruebas unitarias y firma Android.
- Confirmar que el perfil antiguo se migra, que las copias guardadas están cifradas y la edición funciona tras reiniciar.
- Verificar frases por voz y texto en Samsung, Google Search con fuentes reales, y titulares como no contrastados.
- Pruebas de permisos revocados, app cerrada, pantalla bloqueada, modo avión, errores de APIs y restricciones de batería.
- No confundir código en main, pruebas en CI y funcionalidad física en Samsung.

## Referencias de plataforma

- [Google Search grounding](https://ai.google.dev/gemini-api/docs/google-search).
- [Android Keystore](https://developer.android.com/reference/android/security/keystore/KeyGenParameterSpec).
