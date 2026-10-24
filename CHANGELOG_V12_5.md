# SKY IA v12.5: SKY SENTINEL, fases 1 y 2

**Dirección conceptual:** Oscar Elieser Chamorro Guzmán.
Rama `sky-v12.5-sentinel`, que parte de `sky-v12.4`. El informe completo, con vulnerabilidades, pruebas, pendientes y cómo revertir, está en `docs/seguridad/SENTINEL_FASES_1_2.md`.

Objetivo: **que nadie más que vos pueda usar SKY.**

## Lo más importante
- La auditoría encontró **30 rutas de la API que respondían sin la llave del dueño**. Entre ellas:
  - un REPL de Python cuyo *sandbox* se podía evadir;
  - la lectura, exportación y borrado de memorias;
  - tus archivos subidos;
  - las herramientas que gastan créditos.

  Ahora **toda `/api/*` es privada por defecto**: llave del dueño y 2FA si está activo. Sólo quedan públicas la salud, el arranque local, los textos de idioma y el estado del 2FA. Si la verificación falla por un error interno, se niega el acceso.
- **PIN del dueño**, configurable en *Módulos → Seguridad*:
  - la interfaz arranca bloqueada hasta que lo ingresás;
  - lo crítico lo pide en el servidor: enviar correos, aprobar habilidades, exportar tu memoria, acciones de nivel 3, cerraduras y levantar la parada de emergencia;
  - 5 intentos fallidos bloquean 15 minutos.
- **La voz ya no confirma lo crítico.** Un «sí» grabado no alcanza: hace falta un clic, y el PIN si lo configuraste.
- **Modo «sólo este equipo»:** rechaza conexiones remotas aunque traigan la llave. Se activa por voz; desactivarlo pide el PIN.
- **Security Center** a pedido, con estado, dispositivos, eventos de seguridad, auditoría, PIN, pausa de automatizaciones, parada de emergencia y bloqueo.
- **Parada de emergencia ampliada:** también suspende las automatizaciones y las habilidades instaladas.
- **REPL endurecido:** atributos internos, `sympify` y similares bloqueados, con listas cerradas de módulos y *builtins*.
- **Comunidad multiusuario cerrada por defecto** (`SKY_COMUNIDAD_PUBLICA=1` para abrirla). La telemetría de sensores usa su propio token.

## Pruebas
- **751 aprobadas, 0 fallidas**, de las cuales 35 son de SENTINEL e incluyen las **10 pruebas obligatorias** del prompt.
- 8 archivos de pruebas antiguas se ajustaron porque daban por hecho que esas rutas respondían sin llave.
- En Chromium se probó: rutas cerradas, configurar el PIN, la interfaz bloqueada al recargar, un PIN incorrecto rechazado y uno correcto que la abre.
