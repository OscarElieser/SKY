# SKY — Núcleo de aprendizaje operacional compartido

Esta es una **primera integración aditiva** sobre los módulos existentes, no un modelo neuronal reentrenado ni un sistema de autoedición del código.

## Qué queda conectado

- neural_core/sky_core_learning.py: consolida el inventario de módulos **declarados** (sky_module_registry y sky_modulos), resultados de trabajo con evidencia (sky_neural_memory), puntuaciones agregadas del propietario (sky_evolution) y KPIs existentes (sky_metricas).
- neural_core/sky_cerebro.py: añade un resumen contextual limitado y de solo lectura cuando haya experiencia relevante. Esto no altera herramientas disponibles, sus esquemas ni permisos del agente.
- neural_core/sky_aprendizaje.py: entiende preguntas como «SKY, ¿cómo va tu núcleo?» o «estado del núcleo», accesibles mediante el asistente existente.

## Reglas que NO se cambian

1. El núcleo no concede permisos ni activa funciones por estadísticas favorables.
2. Una activación o un resultado KPI no se declara ejecución físicamente verificada. Las acciones SENT, RUNNING, PENDING, DISPATCHED y UI se excluyen del conteo de acciones reportadas.
3. No se copian transcripciones, contraseñas, documentos, parámetros de herramientas, comentarios libres de usuarios ni tokens al resumen operacional.
4. La información del inventario indica existencia en el código, **no** que una integración funcione en el equipo.
5. No hay cambios silenciosos de pesos, LoRA, prompts permanentes, archivos ejecutables ni código.
6. Si una fuente de estadísticas falla, el asistente sigue funcionando con el comportamiento previo.

## Configuración, diagnóstico y reversión

Por defecto, la consulta del núcleo está activa y **no carga modelos pesados**. Para deshabilitarla temporalmente en la configuración local (sin eliminar archivos existentes):

~~~
SKY_NUCLEO_EVOLUTIVO=0
~~~

Para consultar directamente desde PowerShell en el directorio del proyecto, con el entorno virtual existente:

~~~powershell
.\.venv\Scripts\python.exe -c "from neural_core.sky_core_learning import explicar_estado; print(explicar_estado())"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_sky_core_learning.py -v
~~~

La configuración desactiva solo la inclusión del contexto en el cerebro; las funciones de lectura y consulta siguen disponibles. No incluya el PIN ni ninguna credencial en comandos o registros.

## Cobertura y pendientes

Los datos de desempeño se acumulan **únicamente en los módulos que actualmente publican KPIs, feedback o ejecuciones verificadas**. Los demás están visibles en el inventario, pero no se presume que ya produzcan experiencias fiables. Para una cobertura completa faltan adaptadores instrumentados por cada módulo, un esquema único de eventos con evidencia, evaluaciones E2E en Windows/Android y, en una fase separada, un conjunto de entrenamiento LoRA curado, con validación y reversión antes de desplegar el nuevo adaptador.

Las pruebas unitarias nuevas están en tests/test_sky_core_learning.py. Deben complementarse con la suite global y pruebas reales de dispositivos.
