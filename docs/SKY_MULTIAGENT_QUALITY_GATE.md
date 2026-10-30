# SKY Multiagent Quality Gate (2026-10-30)

SKY mantiene un solo orquestador (`sky_unified_agents`) y sus ejecutores supervisados anteriores; este bloque NO crea un segundo asistente, no concede permisos ni ejecuta tareas en el dispositivo.

## Integración real

- `sky_multiagent_quality.advice()` consulta categorías de fallos de pruebas anteriores en la base local de `sky_reflective_core`. Nunca comparte peticiones originales, secretos, código ni errores brutos con el modelo. Los consejos identifican su origen como **pruebas del generador de habilidades**, no como éxitos del subagente ni resultados de dispositivos.
- Para una solicitud compleja **consultiva**, SKY presenta estas comprobaciones en la planificación, en los especialistas y en la síntesis. Las solicitudes que impliquen acciones mantienen el flujo de permisos anterior.
- `assess()` busca ciertas declaraciones de acciones ya realizadas sin pruebas de ejecución. No realiza fact-check externo, no demuestra que el contenido sea verdadero y puede tener falsos positivos/negativos.
- Una respuesta marcada como potencialmente ficticia se vuelve a sintetizar **una sola vez** a partir de los mismos especialistas. Si persiste el problema, SKY retorna al flujo de respuesta anterior sin entregar esa síntesis.
- Las métricas preexistentes registran solamente cantidad de expertos y revisiones; no se almacenan prompts de conversación en la nueva memoria.
- La memoria agrupa más temas: programación, educación, investigación y seguridad, además de categorías generales. El modo Ollama semántico local es optativo.

## API compartida y seguridad

`GET /api/sky/cognition/multiagent-quality` necesita `X-SKY-KEY` y devuelve capacidades y límites. Se usa la **misma API**, que sirve para la app Windows y para Android cuando el cliente esté autenticado y pueda conectarse. No agrega permisos nuevos, no transmite historiales privados y no proporciona acciones ejecutables.

## Verificación

```bash
python -m pytest -q tests/test_sky_multiagent_quality.py tests/test_sky_unified_agents.py tests/test_sky_reflective_core.py tests/test_sky_cognition.py
```

Las pruebas automatizadas no reemplazan ensayos con Windows 10/11 o Android real. Tampoco prueban entrenamiento de pesos ni autonomía irrestricta.
