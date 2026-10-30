# SKY IA — Herramientas reales en la conversación (30/10/2026)

## Integración ejecutable
Las solicitudes compatibles se interpretan mediante el módulo
sky_conversation_tools y se pasan a sky_role_router.dispatch / sky_verified_roles.run_plan.
El resultado incluye proveedor sky-verified-local, estado y número de intentos.

El mismo motor se consulta en:
- sky_asistente_personal.atender → API /api/asistente/mensaje.
- /api/asistente/stream → respuestas NDJSON con evento final para voz y HUD.
- /api/sky/home/chat → respuestas de cálculo local sin elegir proveedor cloud.
- /api/sky/mobile-chat/chat → delega a SKY Home **tras validar un token móvil
  limitado**; no se expone el token maestro ni se conceden permisos de acción.

## Ejemplos de frases completas
- ¿Cuánto es (12 + 8) * 3?
- Dame el promedio de 2, 4 y 6.
- Masa molar de H2O.
- Fuerza de Newton con masa de 3 kg y aceleración de 4 m/s².
- Energía cinética con masa de 3 kg y velocidad de 4 m/s.
- Evalúa rúbrica: Contenido 20/25; Presentación 18/25.

Los datos deben estar en la frase. No se inventan unidades, información
del historial o archivos. No se ejecuta ninguna solicitud ambigua ni se
interpreta un pedido de redes, archivos o apps como cálculo. La ejecución
científica es de alcance limitado; la rúbrica tiene escala orientativa.

## Controles
Las reglas de emergencia, permisos y órdenes de dispositivo mantienen prioridad
en /asistente/mensaje y /stream. SKY Home conserva la autenticación vigente
y el chat móvil mantiene credenciales limitadas; no habilita herramientas
generales ni acciones sensibles. La investigación externa no se ejecuta
automáticamente por el puente, y ninguna respuesta utiliza fuentes no
verificadas como hechos comprobados.

## Evidencia
GitHub Actions ejecuta los tests previos y test_sky_conversation_tools.py,
py_compile y node --check del HUD. Queda por verificar con un teléfono real
la UI, reconocimiento de voz, reproducción multimedia y conectividad remota.
Esta implementación no crea una APK nueva ni instala cambios en Windows.
