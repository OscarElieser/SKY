# Hablarle a SKY por WhatsApp

SKY usa la **API oficial de WhatsApp Business Cloud de Meta**. WhatsApp no tiene una API para cuentas personales, así que SKY necesita **su propio número de WhatsApp Business**. Vos le escribís desde tu WhatsApp de siempre, como a cualquier contacto.

```
Tu WhatsApp ──► número de SKY (Meta) ──► webhook firmado ──► puente de SKY en tu PC (puerto 8770)
                                                              └─► SKY entiende, ejecuta o te pide confirmación
Tu WhatsApp ◄── respuesta de SKY ◄── Graph API de Meta ◄───────┘
```

## Qué podés hacer

- Cualquier cosa que le pedís a SKY por voz o texto: «sube el volumen», «abre Word», «qué tengo para hoy», «recuérdame en 20 minutos llamar a Ana», «aprende sobre energía solar», «mostrame tu rendimiento», «qué borradores tengo».
- **Notas de voz:** SKY las transcribe en tu PC con faster-whisper, si está instalado.
- **Confirmaciones:**
  - lo que tenés autorizado como automático se hace al instante;
  - lo demás te pide «sí» o «no»;
  - lo de **nivel 3** (enviar correos, borrar notas, cortinas) te pide **«CONFIRMO 1234»**, con un código que vence a los 10 minutos.
- **Avisos:** recordatorios, tareas programadas y problemas que detecte SKY te llegan por WhatsApp.
- **Cerraduras:** por seguridad **no se abren por WhatsApp**, sólo desde el HUD.
- **Parada de emergencia:** «para todo» funciona también por WhatsApp. Para reanudar hace falta el HUD.

## Paso 1: crear la app en Meta (una vez)

1. Entrá a <https://developers.facebook.com/> con tu cuenta de Facebook. **Mis apps → Crear app**. Elegí el caso de uso de **WhatsApp** (conectar con clientes por WhatsApp) y asociala a tu portfolio comercial; si no tenés uno, Meta lo crea.
2. En la app: **WhatsApp → Configuración de la API** (API Setup). Ahí ves:
   - un **número de prueba** gratuito y su **Phone number ID**: va a `SKY_WA_PHONE_ID`;
   - **Para** (To): agregá **tu número personal** y verificalo con el código que te llega por WhatsApp.

   > El número de prueba sólo puede escribirle a los números que verificaste. Para un asistente personal es justo lo que necesitás. Si querés un número propio de SKY, agregá uno en **Números de teléfono**. Tiene que ser una línea que **no** esté usando la app de WhatsApp (por ejemplo, un chip nuevo).
3. **Token permanente:** el que muestra *API Setup* vence en 24 h.
   1. Entrá a **Configuración del negocio → Usuarios → Usuarios del sistema → Agregar**, con rol administrador.
   2. **Asignar activos:** tu app, con control total.
   3. **Generar token:** elegí la app, vencimiento **Nunca** y los permisos `whatsapp_business_messaging` y `whatsapp_business_management`.

   Ese token va a `SKY_WA_TOKEN`. Mejor todavía: guardalo en un archivo y usá `SKY_WA_TOKEN_FILE`.
4. **Secreto de la app:** en **Configuración de la app → Básica → Clave secreta de la app**. Va a `SKY_WA_APP_SECRET`. Con él, SKY verifica que cada mensaje viene de Meta.

## Paso 2: configurar SKY

En `.env`:

```
SKY_WA_TOKEN=EAAG...                     # o SKY_WA_TOKEN_FILE=C:\Users\TU_USUARIO\.neuralt\wa_token.txt
SKY_WA_PHONE_ID=123456789012345
SKY_WA_APP_SECRET=la_clave_secreta_de_la_app
SKY_WA_VERIFY_TOKEN=inventa-una-frase-larga-y-unica
SKY_WA_OWNER=50588887777                 # TU número con código de país, sin + ni espacios
```

`SKY_WA_VERIFY_TOKEN` lo inventás vos: es una contraseña que Meta repite al conectar el webhook.

## Paso 3: abrir el puente y publicarlo

1. Abrí `SKY_INICIAR.bat` y elegí **W**. Con la opción **0** el puente arranca solo cuando WhatsApp está configurado. Se abre `http://127.0.0.1:8770/whatsapp/webhook`.
2. Meta necesita una dirección **HTTPS pública**. Con Tailscale instalado:
   ```
   tailscale funnel --bg 8770
   ```
   Te da algo como `https://mi-pc.mi-red.ts.net`.
   - **Sólo se publica el puente**: la API de SKY (8765) y el agente (8766) siguen privados.
   - El puente acepta únicamente `/whatsapp/webhook` y `/salud`, con firma obligatoria.

   Alternativa sin Tailscale: `cloudflared tunnel --url http://127.0.0.1:8770`.
3. En Meta: **WhatsApp → Configuración** (Configuration) **→ Webhook → Editar**.
   - URL de devolución: `https://mi-pc.mi-red.ts.net/whatsapp/webhook`
   - Token de verificación: el mismo `SKY_WA_VERIFY_TOKEN`
   - **Verificar y guardar**. Después, en *Campos del webhook*, **suscribite a `messages`**.
4. Mandale «hola» a SKY desde tu WhatsApp. En el HUD, en **Módulos → Automatización → WhatsApp**, vas a ver *conectado*, y podés enviar un mensaje de prueba.

## Avisos fuera de las 24 horas

Meta sólo deja que un negocio escriba libremente **dentro de las 24 h** desde tu último mensaje. Para que SKY te avise en cualquier momento (por ejemplo, el recordatorio de las 6:00):

1. En **WhatsApp Manager → Plantillas de mensajes**, creá una plantilla de categoría **Utilidad**, en español, con el cuerpo `Aviso de SKY: {{1}}`.
2. Cuando Meta la apruebe, poné en `.env`: `SKY_WA_PLANTILLA=nombre_de_tu_plantilla` (y `SKY_WA_PLANTILLA_IDIOMA=es` si la creaste en otro código de idioma).

Sin plantilla, SKY te avisa en el HUD, el escritorio y el celular (Home Assistant), y por WhatsApp sólo cuando la ventana está abierta. `SKY_WA_AVISOS=0` apaga los avisos por WhatsApp.

## Costos (desde el 1 de octubre de 2026)

- Las respuestas de SKY dentro de la ventana son mensajes de *servicio*. **Cada número tiene 1000 gratis por mes**, y Meta cobra a partir del 1001.
- Las **plantillas** (avisos fuera de la ventana) se cobran por mensaje, según la categoría y el país.
- SKY cuenta lo que envía:
  - en **Rendimiento → Servicio** ves `whatsapp_enviados_mes`;
  - SKY te avisa cuando pasás el 90 % del cupo gratis.
- Precios oficiales: <https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing>.

## Seguridad

- Sólo responde a `SKY_WA_OWNER`. Los mensajes de otros números se ignoran sin contestar y quedan contados en los KPIs.
- Sin la firma `X-Hub-Signature-256` correcta, el mensaje se rechaza (401).
- Hay un límite de 20 mensajes por minuto, y los reintentos de Meta se descartan.
- Los textos no se guardan en los registros. Los últimos 12 turnos quedan en `~/.neuralt/sky_whatsapp.json`, en tu PC.
- Tu WhatsApp es tan seguro como tu teléfono: activá el bloqueo de pantalla y la verificación en dos pasos de WhatsApp.

## Prueba sin Meta

```
python sky_whatsapp_puente.py --probar "qué tengo para hoy"
```

Procesa el texto como si llegara por WhatsApp y muestra la respuesta, sin enviar nada.
