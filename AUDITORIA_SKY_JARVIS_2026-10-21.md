# Auditoría SKY IA — integración JARVIS local

Fecha: 21 de octubre de 2026.
Repositorio: https://github.com/OscarElieser/SKY
Base auditada: main e346bb46acbce97e03c1011ab48c4eb3e2716e0f.
Rama de trabajo: feature/sky-jarvis-local-20261020.
Revisión: https://github.com/OscarElieser/SKY/pull/3

## Alcance y método

Revisión de código en GitHub, árbol del repositorio, agente local, reconocimiento de voz, rutas FastAPI, seguridad de secretos, Docker Compose, pruebas unitarias y logs de GitHub Actions. Las verificaciones de CI son pruebas remotas y no sustituyen una prueba interactiva en la computadora personal Windows del usuario. No se accedió al sistema operativo del usuario ni se cambió producción.

## Hallazgos priorizados

| Prioridad | Observación verificable | Estado |
| --- | --- | --- |
| P0 | Fallaba pip-audit con 17 entradas de vulnerabilidad: cryptography 47, Pillow 12 y setuptools 79. | Rangos/dependencias actualizados en rama. Requiere nueva comprobación final del análisis. |
| P0 | La configuración pública suministra SKY_API_KEY_FILE y SKY_OWNER_MFA_SECRET_FILE, pero la validación sólo consultaba valores inline. | Corregido mediante get_secret(). |
| P0 | Redis exigía contraseña montada, pero su cliente inicial no pasaba SKY_REDIS_PASSWORD_FILE. | Corregido con lectura privada de secretos. |
| P0 | API importaba el módulo intentando crear directorios en sistema de solo lectura. Fallo reproducido en GitHub Actions v10.8: Errno 30 /app/local_data/sky_uploads. | Creación de carpetas trasladada al momento de escritura. Pendiente verificación nueva del contenedor. |
| P0 | El endpoint de bootstrap podía revelar el token del propietario si una solicitud pública parecía provenir de localhost a través de un proxy. | Restringido a SKY_DEPLOYMENT_MODE local; prueba añadida. |
| P1 | Algunas rutas de herramientas de FastAPI (ej. /api/tools/image, /api/tools/video, /api/tools/search) no declaran Depends(require_key) individualmente. | Revisar políticas de autenticación y consumo antes de exponer SKY a Internet. No cambiado por riesgo de afectar flujos existentes. |
| P1 | No había teclas multimedia nativas para Windows en la lista segura de acciones. | Añadidas con lista restringida y ejecución real mediante tecla nativa. |
| P1 | No había CRUD limitado de notas de propietario a través del agente. | Añadidas crear, añadir texto y mover a papelera recuperable, por defecto desactivadas y con confirmación por acción. |
| P1 | Las pruebas de voz en CI no prueban la captación física del micrófono, reconocimiento en habitación real, ni el reproductor del usuario. | Pendiente validación presencial en Windows y mediciones de latencia/error. |
| P2 | Existe un conjunto muy amplio de motores y funciones, pero se necesita separar el razonamiento del ejecutor autorizado y dar resultados comprobables. | Plan de arquitectura recomendado más abajo. |

## Lo que puede ejecutarse en la fase actual

- Abrir sitios HTTPS conocidos o una URL HTTPS indicada, después de la activación autorizada.
- Abrir calculadora, Bloc de notas, explorador de archivos y navegador, cuando estén disponibles.
- Leer estado básico del agente conectado.
- En Windows, enviar teclas multimedia reproducir/pausar, anterior/siguiente, volumen arriba/abajo y silencio.
- Crear notas de texto, añadir texto y mover notas privadas a papelera dentro de ~/.neuralt/notes tras confirmación desde el panel y SKY_NOTES_ENABLED=1.

Limitaciones: enviar una tecla multimedia no acredita que una canción se haya iniciado; no hay todavía catálogo musical/reproducción de canciones específicas, control universal de todas las apps, manipulación arbitraria del escritorio, administración del teléfono, instalación de software, acceso pleno a documentos personales o envío de correos/mensajes mediante voz. No afirmar estos resultados sin evidencia real del ejecutor.

## Modelo de seguridad exigido para siguientes etapas

1. Cualquier texto o voz se interpreta primero como intención propuesta y parámetros estructurados.
2. El plan se valida por capacidades y alcance: sólo apps permitidas, carpetas permitidas o APIs OAuth legítimas.
3. La ejecución se realiza exclusivamente en el dispositivo emparejado del propietario. Nunca ejecutar comandos shell recibidos desde el modelo.
4. Acciones destructivas o externas (borrar fuera de la papelera, mandar correos, compras, ajustes de sistema) exigen vista previa, confirmación de usuario y registro mínimo.
5. El agente debe devolver un recibo comprobable. Los fallos no deben presentarse como éxito.
6. Las credenciales se administran fuera del código y del navegador; prohibido exponer API key de propietario en despliegue público.

## Arquitectura propuesta

- Voz: detector de activación explícita + Vosk/faster-whisper local, con calibración real de micrófono y anti-eco.
- Cerebro: modelo conversacional conectado a datos verificables con citas, incertidumbre y memoria opcional.
- Orquestador: traductor de órdenes a acciones estructuradas, permisos, simulación/vista previa, confirmación y auditoría.
- Agente local: Windows con sesión interactiva, acceso a navegador, medios y sistema de archivos por capacidades; jamás control de shell arbitrario por voz.
- Automatizador web: Playwright en sitios permitidos, perfiles separados, dominio verificado y confirmación para envíos.
- Documentos: edición de DOCX/XLSX/PDF por módulos especializados, previsualización y versionado.
- Integraciones: Gmail/Calendario/Drive mediante OAuth con permisos mínimos y confirmación para acciones externas.
- Móvil: agente Android autorizado separado; no asumir control nativo desde navegador ni acceso a aplicaciones de terceros sin permisos.
- Fiabilidad: métricas de tasa de ejecución real, precisión de intención, WER y latencia; pruebas de regresión y políticas de recuperación.

## Pruebas de aceptación en Windows

1. Tener instalada la voz local Vosk y arrancar INICIAR_SKY_JARVIS_WINDOWS.bat con el modelo correcto. Verificar que el agente se enlaza sólo a 127.0.0.1:18765 (o puerto SKY_DEVICE_PORT configurado).
2. Orden SKY, abre YouTube: debe abrirse realmente el navegador y el agente confirmar petición; repetir con calculadora.
3. Abrir un reproductor multimedia y ordenar SKY, pausa la música; confirmar visualmente que la tecla produjo el resultado esperado.
4. Para notas, habilitar SKY_NOTES_ENABLED=1 sólo en la terminal del agente. Orden SKY, crea una nota agenda que diga reunión lunes; revisar el panel y confirmar. Inspeccionar ~/.neuralt/notes/agenda.txt.
5. Agregar texto a la nota con confirmación; verificar que el texto anterior se conservó.
6. Enviar la nota a papelera con confirmación; comprobar que pasó a .trash y que ningún archivo externo se tocó.
7. Repetir acciones de escritura sin confirmación y sin SKY_NOTES_ENABLED: deben rechazarse.
8. Repetir con URL file://, nombres ../, aplicaciones no permitidas y teclas no incluidas: deben rechazarse.
9. Revisar Actions de PR #3; no fusionar hasta que no queden rojos no explicados y exista una prueba local Windows satisfactoria.

## Secuencia recomendada

Fase 1: consolidar CI, protección de secretos, notas y teclas locales. Fase 2: automatización real y verificable del navegador con permisos; edición versionada de documentos; OCR/visión local asistida si corresponde. Fase 3: conectores con OAuth, calendario/correo y flujos multietapa auditados. Fase 4: agente móvil Android, sincronización segura, monitoreo y pruebas de resiliencia. Mantener BAQUEANO separado, con pruebas y sin cambios de producción.

## Estado de validación

GitHub Actions de commits intermedios de la rama devolvió éxito para el flujo de seguridad y el pipeline completo v11.0; el contenedor aislado v10.8 encontró Errno 30 de sistema de sólo lectura, diagnosticado y corregido posteriormente en la rama. Es imprescindible confirmar los checks del último commit. No se declara desplegado ni probado en el equipo Windows del propietario.
