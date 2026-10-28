# SKY AI — Subasta supervisada de proveedores (v1)

La subasta elige un motor para **cada solicitud**, sin reemplazar SKY CORE, su
API (8765), el agente Windows/Android ni las políticas de autorización.

## Activación en el equipo

1. Respaldar el `.env` privado (nunca publicarlo).
2. Configurar allí:

```dotenv
SKY_CEREBRO=subasta
SKY_LOCAL_ONLY=0
SKY_AUCTION_MAX_ATTEMPTS=2
```

3. Mantener las claves API que ya estén configuradas. No se copian al repositorio.
4. Reiniciar el supervisor de SKY para recargar las variables del proceso.

No modificar `SKY_API_KEY`: es la autenticación de la **API propia** y no una
clave de un proveedor externo.

## Funcionamiento actual

- **Clasifica** la solicitud como general, investigación, programación, documentos
  o voz.
- **Calcula ofertas** para OpenAI, Gemini, Anthropic, Groq, DeepSeek, Mistral
  y Ollama. No incluye otros servicios que no tengan adaptador de herramientas
  compatible con el cerebro de SKY.
- Usa **preferencias iniciales configuradas en el código**, no rankings
  científicos. Con al menos tres muestras recientes ajusta la puntuación por
  errores y latencia realmente registrados en los últimos siete días.
- Una clave API presente **no significa** que sea válida, tenga cuota o
  funcione en ese momento. Se verifica al consultar el proveedor.
- Consulta **una IA a la vez**; ante fallo puede intentar con otra autorizada,
  hasta el límite configurado. No mezcla respuestas parciales.
- Los llamados a herramientas siguen generando **propuestas** y requieren
  validación por el mismo agente y política del dueño. No se ejecutan
  simultáneamente en varias IA.
- Se registran proveedor, tiempo, éxito y cantidad de tokens cuando la API
  informa esos valores; no se guardan las consultas ni las claves.
- `SKY_LOCAL_ONLY=1` bloquea la subasta en la nube. Textos con indicadores
  evidentes de PIN, contraseña o tokens también se restringen al motor local.
  El detector textual de datos sensibles **no reemplaza** una clasificación
  integral de privacidad.
- `SKY_CEREBRO=auto` conserva Ollama local como opción anterior, para evitar
  que equipos existentes envíen datos a la nube inesperadamente.
- Elegir manualmente un proveedor en el HUD prevalece sobre la subasta.

### Alcances y pendientes de validación

Este es un **enrutador de ofertas por historial y tipo de tarea**, no un juez que
compare todas las respuestas contra una verdad externa. No genera siete
respuestas para escoger la más larga. Para tareas académicas es obligatorio
verificar fuentes; para cambios del equipo, confirmar la acción real.

La subasta no impone por sí sola un techo monetario garantizado, porque
distintos proveedores facturan modelos y tokens con tarifas variables. Ajustar
cuotas de cada plataforma y revisar el consumo antes de permitir más intentos.

Las pruebas unitarias no ejecutan solicitudes facturables. La disponibilidad
real de API y modelos debe probarse **en la PC** que contiene el `.env`.

## Comprobar las ofertas sin consumir API

```powershell
Set-Location "C:\Users\PC 1\Documents\Desktop\SKY"
@'
from dotenv import load_dotenv
load_dotenv(".env")
from neural_core.sky_ai_auction import ofertas
from neural_core.sky_cerebro import motor
print("Motor seleccionado:", motor("investiga una publicación científica"))
for o in ofertas("investiga una publicación científica"):
    print(o["proveedor"], "puntos:", o["puntuacion"], "muestras:", o["muestras"], o["motivo"])
'@ | .\.venv\Scripts\python.exe -
```

Después probar una **consulta real corta** desde el HUD y revisar los KPI de
modelo. No publicar las claves, los tokens ni el archivo `.env`.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_sky_ai_auction.py -v
```
