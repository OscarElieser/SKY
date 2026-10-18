# SKY IA Social Universe v7.0 — Piloto multijugador real

**Visión y concepto:** Oscar Elieser Chamorro Guzmán.
**Idea central:** «Un mundo real a digital donde la imaginación brinde oportunidades de sentirse vivo».

### Implementaciones verificadas

- Registro mediante invitación única, autenticación de usuarios y perfiles persistentes.
- Mundos 3D públicos **solo por decisión del propietario**.
- Múltiples usuarios simultáneos, avatares, navegación WASD y controles táctiles.
- Chat WebSocket real, persistencia de mensajes SQLite, presencia, posiciones y desconexiones.
- Muro social con publicaciones, reacciones, seguidores y reportes.
- Llamadas WebRTC entre dos usuarios como función de navegador (pendiente prueba micrófonos/red real; necesita TURN para algunos escenarios).
- Memoria aislada por usuario, olvidos, feedback y recuperación contextual para SKY local u otro proveedor permitido.
- Conserva las características SKY v6: motor API, GLB y metaverso editable, finanzas, IA de proveedores, voz, sensores y BAQUEANO Control Center.

### Instalación rápida

**Windows**: ejecutar `INICIAR_SKY_SOCIAL_WINDOWS.bat`, luego abrir `http://127.0.0.1:8765/community`.
**macOS/Linux**: ejecutar `bash iniciar_sky_social_linux_mac.sh` y abrir la misma URL.

1. Al iniciar se crea la clave del propietario en `local_data/sky_api_token.txt`.
2. Entrar como propietario a la página `/` o usar la opción «Propietario» del panel social.
3. Con la clave del propietario, crear/publicar un mundo desde la comunidad.
4. Generar una invitación **distinta para cada usuario**.
5. Cada usuario se registra y accede a SKY desde una pestaña/perfil distinto.
6. Dos participantes pueden entrar al mismo mundo, moverse y chatear en tiempo real.
7. La configuración de Gemini, Claude, OpenAI y Ollama es opcional para conversar libremente. La experiencia social y los recuerdos funcionan sin claves externas.

**Pruebas:** 85 comprobaciones locales, incluyendo dos usuarios con WebSocket, memoria aislada y señalización de voz. `python -m pytest -q` después de instalar `pytest`, `httpx` y dependencias; todos los tests originales de v6 siguen incluidos.

### No confundir capacidades actuales con visión a futuro

**Real ahora:** servidor con base de datos, API autenticada, presencia y mensajes multiusuario, escena 3D con avatares geométricos, sesiones y red social básica.
**Pendiente:** prueba física de voz, mundos con física avanzada, edición 3D multijugador con resolución de conflictos, VR real, modelado hiperrealista, economía virtual, tiendas de activos, MMO con escalado horizontal, hosting público y disponibilidad 24/7.

**Registro legal:** el expediente incluido refleja la concepción del proyecto, pero **no acredita que una autoridad haya registrado SKY IA**. Para marca y programa de cómputo, consultar el Registro de la Propiedad Intelectual del MIFIC y presentar la solicitud oficialmente.

Ver [`SKY_COMMUNITY_API.md`](SKY_COMMUNITY_API.md) y [`AUTORIA_SKY_IA_Oscar_Elieser_Chamorro_Guzman.md`](AUTORIA_SKY_IA_Oscar_Elieser_Chamorro_Guzman.md).

**Copias de seguridad:** ejecutá `python sky_backup.py` en el equipo servidor para copiar las bases de datos SQLite a `backups/`. Las copias tienen permisos privados y se verifican con `PRAGMA integrity_check`. Protegé y cifrá los respaldos antes de trasladarlos a otro equipo.
