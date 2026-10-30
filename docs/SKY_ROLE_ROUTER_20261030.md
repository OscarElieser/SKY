# SKY — Enrutamiento verificable y estado de roles

Esta actualización añade un selector conservador sobre ocho herramientas ejecutables
existentes. No sustituye el cerebro, los permisos Android/Windows ni los controles de
aprobación. Las solicitudes ambiguas o desconocidas no se ejecutan; la selección
no deduce parámetros ni crea nuevas herramientas.

GET /api/sky/verified-roles/dashboard: estadísticas de herramientas.
POST /api/sky/verified-roles/recommend: {"task":"fuerza de Newton"}.
POST /api/sky/verified-roles/dispatch:
{"task":"fuerza de Newton","args":{"modelo":"segunda_ley_newton","masa_kg":3,"aceleracion_m_s2":4}}.

La llamada dispatch es explícita y delega únicamente en run_plan. Un historial de
al menos cinco muestras locales con más del 50% de fallos obliga revisión.
Las muestras de investigación no certificadas no cuentan como éxitos.

HUD > Módulos > Agentes verificados > VER FIABILIDAD: ventana con acceso
autenticado y datos agregados; solo usa textContent, nunca HTML desde la API.

CI incluye tests de router, suites anteriores y node --check. Sin pruebas
físicas todavía; no se declara APK instalada ni reentrenamiento de pesos.
