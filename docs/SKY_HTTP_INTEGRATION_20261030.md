# SKY — Verificación de rutas HTTP reales sin ejecutar aplicaciones

Se añade suite HTTP independiente que crea una aplicación FastAPI con routers
auténticos de SKY (herramientas verificadas, SKY Home y chat móvil).
Únicamente la dependencia de clave de propietario se sustituye por un verificador
de prueba. No usa servicios externos, no inicia un dispositivo Windows ni
Android, no crea credenciales reales y tampoco prueba MFA de producción.

Comprueba por HTTP:
- la necesidad de encabezado propietario en /dashboard y /sky/home/chat;
- el despacho de cálculos mediante el router real;
- la validación JSON en SKY Home sin proveedor LLM ni red;
- el rechazo de un token de agente móvil usado como token de conversación;
- invitación, emparejamiento y revocación mediante los módulos reales SQLite;
- un cálculo aritmético con token móvil válido, sin permisos de dispositivo;
- entrada JSON inválida sin falso éxito.

La suite usa TestClient de FastAPI con dependencias mínimas instaladas solo
en CI. Debe ejecutarse además de los unit tests; un TestClient no es evidencia
de funciones físicas en un teléfono ni de una APK compilada.
