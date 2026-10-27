# SKY — Alimentación del núcleo desde internet

## Implementación

SKY reutiliza el lector público Google News RSS de neural_core/actualidad.py y añade neural_core/sky_web_learning.py. Su base SQLite contiene referencias públicas fechadas. No sustituye sky_aprendizaje, sky_neural_memory, la API propia ni modelos instalados. La investigación manual de Wikipedia sigue disponible.

- Al arrancar la API, el nuevo proceso espera una hora antes de consultar internet. Después revisa los temas cada hora.
- Cada tema se consulta máximo una vez cada 24 horas, con tres temas por ciclo y hasta ocho titulares por tema.
- Temas predefinidos: agentes de inteligencia artificial, seguridad de software y educación técnica.
- Los únicos enlaces admitidos en el nuevo almacén son los HTTPS de news.google.com, con fecha válida de los últimos siete días.
- Las referencias se deduplican, se conservan como máximo 30 días y tienen un máximo de 600 registros.
- El cerebro utiliza como máximo dos titulares relacionados, citados, etiquetados como fuentes externas no verificadas.
- No se envían conversaciones privadas, documentos ni credenciales a Google News RSS.

## Límites

No verifica hechos, no lee artículos completos, no cambia pesos del modelo, permisos, código ni entrenamientos LoRA. No significa que los 58 componentes catalogados estén plenamente integrados ni que su actividad se aproveche toda. La capa opera solo si la API de SKY está funcionando y el proveedor responde.

## Configuración en el .env local

SKY_INTERNET=1
SKY_WEB_LEARNING=1

Opcional, temas públicos separados por punto y coma:

SKY_WEB_LEARNING_TOPICS=agentes de inteligencia artificial;seguridad de software;educación técnica

SKY_LOCAL_ONLY=1 impide todas las nuevas consultas externas. SKY_WEB_LEARNING=0 desactiva la sincronización independiente. No incluya claves ni PIN en archivos del repositorio.

## Validar en Windows (PowerShell)

    git pull --ff-only origin main
    & .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_sky_web_learning.py" -v
    & .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_sky_core_learning.py" -v
    & .\.venv\Scripts\python.exe -c "from neural_core.sky_web_learning import status; print(status())"

Sincronización manual (hace tráfico externo si está permitido):

    & .\.venv\Scripts\python.exe -c "from neural_core.sky_web_learning import sync; print(sync())"

También se pueden usar los comandos por voz o texto:
- SKY, alimenta tu núcleo con internet
- SKY, estado del aprendizaje web

La sincronización manual respeta el límite de una consulta por tema cada 24 horas. Las pruebas no usan red real; la disponibilidad final se confirma en el ordenador mediante sync y status.

## Próximas fases

Conectar documentación técnica oficial de fuentes permitidas, cotejar afirmaciones, registrar resultados verificables de cada herramienta y construir un conjunto de evaluación autorizado para LoRA. Ningún entrenamiento ni despliegue debe ejecutarse a partir de contenido web no revisado.
