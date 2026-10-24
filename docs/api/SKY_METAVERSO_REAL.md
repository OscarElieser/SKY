# SKY Metaverso — correcciones verificables y ruta de madurez

## Lo que existe hoy

SKY **ya tiene** /world con render WebGL procedural, fallback Canvas2D, edición
de objetos, persistencia SQLite, versiones optimistas, exportación GLB,
WebXR experimental y presencia por WebSocket. Esta implementación no se
sustituye ni se elimina. Los mundos no son fotogrametría de alta fidelidad ni
simulaciones físicas de videojuegos.

## Correcciones incorporadas

- **MFA del propietario:** `/world` reutiliza el helper existente
  `SKYOwnerAuth.begin(secret)`, transmite `X-SKY-SESSION` en las llamadas
  privadas y revoca su sesión mediante `logout`. No se inventó un sistema
  de autenticación nuevo.
- **Reconexión de salas:** ante caída WebSocket, vuelve a pedir ticket nuevo,
  aplica reintentos con espera creciente y descarta conexiones viejas cuando
  cambiás de mundo o cerrás sesión. No reutiliza tickets temporales.
- **Desplazamiento accesible:** WASD/flechas funciona en el motor WebGL **y**
  en su visor de reserva Canvas2D. Los botones táctiles se muestran en
  dispositivos con puntero táctil y también se pueden activar con teclado.
- **Posiciones compartidas:** envía la posición del avatar por WebSocket,
  con límite de frecuencia y envío diferido para no perder el último movimiento.
- **Pruebas de integración:** verificación de SQLite, versiones de escenas,
  GLB real, ticket de un solo uso, WebSocket (posición y chat), autorización
  y contrato de navegación.

## Iniciar y comprobar en la computadora

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_sky_metaverse_reliability.py
.\.venv\Scripts\python.exe -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
```

Abrí `http://127.0.0.1:8765/world` y entrá con la clave de SKY. Si
SENTINEL requiere el segundo factor, proporcioná el código en el cuadro
del sistema. Creá un mundo, agregá una pieza, guardá, refrescá y verificá que
sigue allí. Exportá a GLB. Movete con WASD/flechas; en pantalla táctil
usá las flechas visibles. Probá la desconexión y recuperación de red para
comprobar la nueva sala.

**Importante:** CI confirma la API y prueba sintaxis JavaScript, pero no
sustituye una prueba real de GPU/navegador, Android, WebXR ni una revisión
de rendimiento bajo carga. No fusionar sin esas pruebas de uso.

## Brechas para un metaverso inmersivo profesional

| Prioridad | Mejora necesaria | Condición observable para declararla lista |
| --- | --- | --- |
| P0 | Pruebas interactivas en Chromium, Edge, Android y Firefox + pérdida/restauración del contexto WebGL | Crear/guardar/recargar/editar/exportar y reconectar, sin errores en navegadores objetivos |
| P0 | Endurecer salas para multiusuario: límites, identidad por usuario, permisos de escena, moderación y auditoría | Un usuario nunca edita escenas de otro sin permiso; reingreso y desconexión comprobables |
| P1 | Avatares 3D con animación y personalización (GLB/glTF), cámara tercera/primera persona y controles | Caminar y verse mutuamente con apariencia elegida y movimientos sincronizados |
| P1 | Motor de colisiones y físicas deterministas con límites de CPU, sin código arbitrario | Obstáculos sólidos, gravedad y desplazamiento estable verificados |
| P1 | Importador seguro de modelos glTF/GLB con cuotas, validación y optimización | Modelos autorizados y sanitizados importados, guardados y renderizados realmente |
| P1 | Escenas visuales enriquecidas (materiales, iluminación, sombras, texturas, audio espacial) y adaptativas | Presupuesto de fotogramas/VRAM medido en equipos modestos y potentes |
| P1 | Generador de escenas con IA que devuelva JSON validado por el motor actual | Una instrucción detallada modifica objetos reales y permite deshacer cambios |
| P2 | Escalamiento de presencia mediante broker/Redis, distribución de salas y recuperación entre workers | Dos instancias distintas comparten presencia, mensajes y eventos bajo carga |
| P2 | Voz multijugador mediante WebRTC con permisos de micrófono, STUN/TURN y, para grupos, SFU | Comunicación real bidireccional probada, con silenciar/bloquear/reportar |
| P2 | Interacciones de docencia, laboratorios, reuniones y desafíos con objetos con estado | Cada actividad guarda resultados individuales y tiene controles docentes |
| P2 | XR en visores compatibles con HTTPS real y controladores | Sesiones probadas con visor físico, entrada y salida sin pérdida de datos |

No instalar indiscriminadamente cientos de bibliotecas ni reescribir de una vez
el motor WebGL. Evaluar un motor de escenas como Three.js o Babylon.js sobre
una capa de compatibilidad; un motor de físicas WebAssembly como Rapier podría
servir para colisiones y cuerpos rígidos. Ninguna de estas dependencias nuevas
se ha añadido en esta corrección: su incorporación exige integración real y
pruebas. Preservar la API SKY y el exportador GLB.

### Criterios mínimos para liberar

- CI verde con pruebas backend, JavaScript y seguridad.
- Navegación física local con ratón, teclado y pantalla táctil.
- Dos clientes reales conectados a la misma sala, movimiento visible y chat.
- Escena que conserva contenido tras cerrar/reabrir y conflicto versionado 409.
- GLB que abre en Blender u otro visor independiente.
- Sin pérdida de datos al cambiar de mundo, reconectar o salir.
- Métricas de FPS, latencia, memoria, uso GPU, tamaño de escena y éxito real
  por dispositivo y sesión.
- No informar `completado` cuando una función solo fue simulada.

## Ampliación: SKY World Builder, caminata con colisión y avatares

### Constructor geométrico avanzado

La ruta privada `POST /api/worlds/{wid}/build-campus` recibe
`{"prompt":"Centro educativo de tres plantas con laboratorio de informática, aula interactiva y videoconferencias","seed":42,"version":1}`.
Genera **objetos reales en el formato existente** (edificios, plantas exteriores,
ventanas, salones como volúmenes, árboles, bancos y caminos), validados mediante
el motor SKY y persistidos en la base SQLite actual. Devuelve `world` y `plan`
con elementos reconocidos y límites explícitos.

- En `/world`, el botón **Construir campus avanzado** utiliza la misma ruta.
  También acepta instrucciones de creación de campus en el chat del metaverso
  —incluido texto dictado— siempre con confirmación antes de sustituir geometría.
- El constructor **no** crea muebles internos, aulas equipadas, estudiantes,
  escaleras utilizables ni clases animadas. El número de plantas es una
  representación geométrica externa.
- Solicitudes fuera de los escenarios educativos reconocidos devuelven HTTP 422
  sin sobrescribir el mundo. Conflictos de versión dan HTTP 409; el generador
  original sigue disponible.
- No se envían los textos a un proveedor remoto y no se producen modelos
  3D que no existen en el repositorio.

### Colisión de caminata

`metaverse/static/sky-world-physics.js` implementa detección geométrica
rectángulo-círculo con rotación y movimiento por ejes, a partir de objetos
persistidos. Impide atravesar obstáculos cercanos y salirse de los límites
del terreno actual; en una pared permite deslizarse por el eje libre.
El algoritmo está probado con Node sin mocks de la colisión.

**No** es gravedad, ragdoll, simulación de vehículos ni físicas de
sólidos rígidos. Se ejecuta en el cliente y **no** equivale a la validación
autoritaria de posiciones en un servidor multijugador público.

### Avatares de escena

Los usuarios conectados ven un avatar geométrico en WebGL con cuerpo, cabeza,
brazos y piernas, además de una representación simplificada en Canvas2D.
El propietario puede elegir un color; el servidor WebSocket valida que sea
un RGB hexadecimal, lo comparte en su sala y no lo guarda fuera de la sesión.
La caminata local muestra una animación procedural de piernas.

No se afirma soporte de esqueletos, capturas de movimiento, rostros realistas,
persistencia de apariencias por cuenta ni rigging glTF; son trabajo posterior.

### Verificación técnica adicional

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_sky_world_builder.py tests/test_sky_metaverse_reliability.py
node --test tests/test_sky_world_physics.cjs
node --check metaverse/static/sky3d.js
```

Pruebas físicas por hacer antes de fusionar: GPU y Canvas2D reales, dos ventanas
simultáneas, bloqueo de paso en una pared, reconexión, movimiento en Android,
efectos sobre proyectos guardados y uso de visores WebXR.
