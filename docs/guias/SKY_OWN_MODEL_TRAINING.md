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