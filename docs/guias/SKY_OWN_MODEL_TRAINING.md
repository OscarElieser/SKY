# Entrenamiento del modelo propio especializado SKY

Estado: pipeline LoRA reproducible incorporado, pero NO se ha entrenado un checkpoint ni activado uno en el equipo del propietario.

## Modelo y derechos
Se requiere un modelo open-weight local compatible, datos propios o expresamente licenciados y permiso explícito por ejemplo.
No se leen automáticamente conversaciones, archivos, cuentas ni correos privados. El JSONL debe tener al menos 20 líneas aprobadas.
Cada fila debe usar las claves instruction, response, approved_for_training=true.

## Entrenamiento privado manual
Requiere GPU NVIDIA CUDA, PyTorch compatible, transformers, peft, accelerate y safetensors.
Instalar voluntariamente los requisitos de requirements_sky_training.txt; no se instalan en el inicio de SKY.

Ejemplo de comando PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements_sky_training.txt
.venv\Scripts\python.exe -m neural_core.sky_train_model --dataset C:\SKY-Private\train.jsonl --base-model C:\SKY-Models\MODELO_VERIFICADO --output C:\SKY-Private\checkpoints\sky-v1 --epochs 1 --steps 100 --confirm-rights
```

El programa comprueba derechos, requiere base local con config.json, se niega a reutilizar un destino ocupado y no descarga modelos.
Valida held-out aproximadamente 10%, evalúa la pérdida antes y después y guarda adaptador LoRA safetensors, tokenizer y un manifiesto.
El manifiesto siempre indica activated=false. La evaluación en GPU no se ha ejecutado desde este entorno.

## Condiciones para declarar un modelo propio realmente operativo
Hay que generar un checkpoint de verdad, revisar que no memorice datos privados, medir pruebas ciegas frente al motor previo, verificar los nueve idiomas, comprobar consumo de GPU y crear un servidor de inferencia aprobado que lo cargue. Ningún resultado está garantizado.
LoRA especializa un modelo base; no es entrenamiento fundacional desde cero. Los pesos base y el núcleo SKY se conservan.

## Seguridad
Nunca subir dataset, claves, checkpoints personales o rutas sensibles a GitHub. No entrenar o activar desde órdenes automáticas ni reemplazar las API existentes.
Documentación técnica: https://huggingface.co/docs/transformers/peft

## Inicio del entrenamiento de SKY: lote v1

El repositorio incluye **81 ejemplos originales y sintéticos** en
`data/training/sky_seed_v1.jsonl`, con permiso expreso registrado para
usar estos textos creados para SKY. No incluyen correos, historiales privados
ni datos personales extraídos de la cuenta del propietario.

Además contiene **22 pruebas independientes** en
`data/evaluation/sky_holdout_v1.jsonl` para la evaluación humana y
operativa. No mezclar ese archivo con el entrenamiento: medir aprendizaje
con preguntas vistas produciría una conclusión engañosa.

El tamaño de 81 ejemplos es adecuado para empezar a comprobar el flujo
LoRA, **no para asegurar una especialización profesional**.
Los ejemplos son principalmente reglas de trabajo, control autorizado,
multimedia, integraciones, docencia y nueve idiomas. Antes de entrenar
una versión pública hacen falta más datos diversos, revisados y con licencias.

### Primera ejecución: preflight que NO entrena

Después de actualizar desde `main` y crear tu entorno Python:

```powershell
.\.venv\Scripts\python.exe -m neural_core.sky_train_model --preflight --dataset data/training/sky_seed_v1.jsonl --base-model "C:\SKY-Models\MODELO_LOCAL_COMPATIBLE" --output "C:\SKY-Private\checkpoints\sky-lora-v1"
```

La salida informa cantidad de datos aprobados, entrenamiento/validación,
versión de sistema, paquetes, GPU CUDA y disponibilidad del modelo base
en el disco. No envía los datos a Internet, no descarga pesos ni modifica
el modelo predeterminado.

### Segunda ejecución: entrenamiento real con autorización y GPU

Únicamente cuando `ready_to_train=true` y el propietario haya verificado
la licencia del modelo base y los derechos sobre el dataset:

```powershell
.\.venv\Scripts\python.exe -m neural_core.sky_train_model --dataset data/training/sky_seed_v1.jsonl --base-model "C:\SKY-Models\MODELO_LOCAL_COMPATIBLE" --output "C:\SKY-Private\checkpoints\sky-lora-v1" --steps 100 --epochs 1 --max-length 512 --confirm-rights
```

El script guarda un adaptador LoRA desactivado, un manifiesto con los
resultados y el hash SHA256 del dataset, para identificar exactamente
qué datos se usaron. Entrenar no activa el nuevo modelo.

### Tercera ejecución: aceptación antes de usarlo

Comparar el modelo base y el adaptador en el banco independiente de 22 casos:
precisión, límites, respuestas en nueve idiomas, manejo de acciones y permisos,
latencia y ausencia de filtraciones. Verificar también voz, control Windows,
archivos multimedia y cuentas externas en el equipo real.

```powershell
.\.venv\Scripts\python.exe -m scripts.sky_windows_acceptance --probe-ollama
```

El informe ahora incluye cuatro pilares con indicadores explícitos y
marca todo lo que no se ha probado. No sustituye las pruebas manuales.
No utilizar `SKY_TRAINED_ENABLED=1` antes de validar el checkpoint
con el propietario. Mantener siempre los proveedores anteriores para
poder revertir.

**Situación demostrada hasta ahora:** corpus y preflight en GitHub;
sin modelo base local ni GPU del equipo disponibles en este chat.
Ningún checkpoint especializado ha sido generado por esta ejecución.

## Banco de evaluación ciego tras el entrenamiento

El comando siguiente **solo muestra la estructura del banco** y no utiliza GPU ni genera respuestas:

```powershell
.\.venv\Scripts\python.exe -m scripts.sky_lora_evaluate
```

Solo después de que exista un adaptador real validado y se haya habilitado expresamente para pruebas locales:

```powershell
.\.venv\Scripts\python.exe -m scripts.sky_lora_evaluate --execute --output "C:\SKY-Private\evaluacion-lora-v1.jsonl"
```

Las 22 respuestas se guardan para revisión humana con los criterios de cada caso, **sin una nota automática inventada**. No exponer los resultados privados ni marcar un checkpoint como listo para producción sin aprobar seguridad, claridad, multilenguaje y comparación con el modelo base.
