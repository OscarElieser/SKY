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


## Diagnostico de API (sin mostrar claves)

Una puntuación alta en la subasta **no confirma** que una API funcione.
Si la subasta devuelve error, revisar el código seguro de cada proveedor:

```powershell
# Sin consumir cuotas: modelos configurados, nunca muestra claves.
.\.venv\Scripts\python.exe -m neural_core.sky_ai_diagnostics

# Prueba REAL, facturable, con una pregunta pública mínima por proveedor.
.\.venv\Scripts\python.exe -m neural_core.sky_ai_diagnostics --live --providers gemini openai

# Opcionalmente, comprobar los otros cuatro motores con claves.
.\.venv\Scripts\python.exe -m neural_core.sky_ai_diagnostics --live --providers anthropic groq deepseek mistral
```

Los mensajes muestran **HTTP 401** (autenticación), **403** (permiso),
**404** (modelo/ruta), **429** (cuota/rate limit), **400/422**
(formato y parámetros) o **error de red**. Los códigos públicos del
proveedor pueden acompañar al número HTTP; no se imprime el mensaje
bruto de la API, claves, URLs, conversaciones ni respuestas.

La prueba usa únicamente el texto `Di solamente la palabra OK.`
sin memoria personal y sin ejecutar herramientas. Cada prueba puede
consumir cuota, aunque la respuesta no sea válida. No pegar el contenido
de `.env` ni la clave completa en una conversación.

El enrutador muestra ahora los errores seguros de **cada intento**, en
vez del mensaje genérico que ocultaba si el problema era Gemini, OpenAI
o ambos. En caso de error, `ultimo_proveedor()` indica el último
proveedor **intentado**, no uno que respondiera correctamente.


## Rescate gratuito en Ollama al agotar las API

La subasta tiene una ruta local de respaldo **habilitada por defecto**:
`SKY_AUCTION_LOCAL_FALLBACK=1`. Cuando fallan los proveedores externos
dentro del límite de intentos, SKY consulta Ollama **una única vez**
si está funcionando y tiene un modelo instalado. El rescate local no
incrementa el consumo de API y no requiere subir
`SKY_AUCTION_MAX_ATTEMPTS` a 7.

Ejemplo: `SKY_AUCTION_MAX_ATTEMPTS=2` significa como máximo **dos**
solicitudes a proveedores de pago, seguidas de **un** intento local
si las dos fallan. Si la primera IA responde, no se consulta Ollama.
Si Ollama está apagado o sin modelo, SKY informa el error real; no
finge haber completado la tarea. Se mantiene la política de
confirmación de acciones, y jamás se reenvían acciones ejecutadas.

Para comprobarlo en Windows:

```powershell
ollama list
& .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_sky_ai_auction.py -v
```

El respaldo se puede desactivar con `SKY_AUCTION_LOCAL_FALLBACK=0`.
Los errores externos siguen mostrando su código seguro sin incluir
claves API ni conversaciones.

## Continuidad del servicio al fallar una API

Con `SKY_AUCTION_MAX_ATTEMPTS=2` SKY intenta como máximo dos motores
por solicitud. Si ambos fallan, no alcanza a consultar a los demás.

Para permitir hasta cuatro alternativas:

```dotenv
SKY_AUCTION_MAX_ATTEMPTS=4
```

Se permite configurar entre **1 y 7** motores. Siete es el máximo
posible (seis API cloud y Ollama), pero no se consultan todos si uno
responde. Cada solicitud real puede consumir cuota, aun cuando falla.

Los errores HTTP 503 suspenden el proveedor temporalmente por 45 s;
HTTP 429 sin causa específica por 90 s. Fallos 401/402/403/404 y
errores 429 asociados a saldo o cuota quedan en espera 600 s, para
evitar repetir solicitudes improductivas. Son suspensiones **en memoria
del proceso**: no sobreviven a un reinicio del servidor y no sustituyen
la gestión de facturación ni un circuit breaker distribuido.

El operador puede inspeccionar la espera actual con:

```python
from neural_core.sky_ai_auction import en_espera
print(en_espera())
```

Si Google devuelve `503 UNAVAILABLE`, comprobar estado del servicio y
esperar a que se recupere. Si OpenAI devuelve `429`, revisar el
código de error seguro para distinguir límite de solicitudes de saldo,
uso o gasto. No repetir automáticamente un error de facturación.
