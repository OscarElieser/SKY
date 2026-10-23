# SKY Sports Center — Real Madrid (módulo opcional)

La personalidad deportiva de SKY celebra al Real Madrid, pero **no manipula hechos, fuentes ni probabilidades**. Ofrece pronósticos orientativos (Poisson básico), agenda, noticias y acceso a operadores oficiales. No promueve apuestas.

## Configuración

1. Obtené una clave personal en https://www.football-data.org/ y guardala en el archivo local \`.env\`, **nunca en Git**:
   \`SKY_FOOTBALL_DATA_TOKEN=tu_clave\`.
2. Ejecutá la interfaz Streamlit habitual y abrí **⚽ SKY Sports Center**. El diseño toma como **referencia de navegación** https://futbollibrefullhd.org/: agenda diaria, buscador, filtro por competición, catálogo de canales y área de pantalla. Se implementa con interfaz propia, sin copiar su código ni sus reproductores.
3. Elegí **Agenda de partidos** para buscar por fecha, club o torneo; **Canales** para consultar la guía; **Real Madrid**, **Predicciones** o **Noticias**. Todas son consultas informativas.
4. Solo para mostrar la pantalla de video, escribí o dictá exactamente una orden explícita como \`SKY, muéstrame el partido en vivo del Real Madrid\` y presioná el control de ejecución. Ni abrir la sección ni leer resultados arranca el reproductor.
5. La orden **no** se ejecuta sin intención explícita; consulta estado actual y muestra enlace oficial solo si la API confirma partido en directo. El operador requiere autorización, región y, generalmente, suscripción. Algunos contenidos no ofrecen reproducción incrustada: en ese caso se abrirá la página oficial.

## Reproductor dentro de SKY (solo con permiso del operador)

Si el operador de TV entrega una URL HTTPS **oficial y expresamente autorizada para insertar en sitios externos**, el administrador puede configurar estas variables privadas en \`.env\`:

\`SKY_SPORTS_EMBED_URL=https://operador-autorizado.example/reproductor\`

\`SKY_SPORTS_ALLOWED_EMBED_HOSTS=operador-autorizado.example\`

La URL y dominio son **ejemplos, no señales operativas**. El dominio debe ser idéntico al del proveedor autorizado. Al ejecutar la orden explícita, si la fuente deportiva confirma un partido en directo, SKY presentará el reproductor dentro de la aplicación; el usuario deberá iniciar la reproducción. Si no existe autorización de inserción, mostrará el enlace al servicio oficial. Algunos servicios usan DRM y bloquean los iframes: no se intentará eludirlo. Nunca cargará videos al abrir la agenda o ver noticias.

## Derechos audiovisuales

La guía orientativa para Nicaragua usa:
- LaLiga: ViX Premium / Sky Sports, según derecho y plan disponibles.
- Champions League: ESPN figura como operador regional de Centroamérica según UEFA.

Ningún enlace de terceros del tipo Fútbol Libre se utiliza para extraer reproductores, tokens o señales. No se ofrecen proxies de TV, DRM bypass ni retransmisiones sin licencia.

## Fuentes y límites

- [football-data.org v4](https://docs.football-data.org/general/v4/coding_client.html): resultados y partidos. La cobertura y cuotas dependen del plan del usuario.
- [LaLiga, operadores oficiales](https://www.laliga.com/es-US/donde-ver-laliga-easports).
- [UEFA, canales oficiales](https://www.uefa.com/uefachampionsleague/news/0253-0d82037aaedd-f371c464f919-1000--where-to-watch-the-uefa-champions-league-tv-broadcast-partne/).

La interfaz realiza consultas solo al pulsar botones o dar comandos; no se inicia streaming en segundo plano. La API puede no cubrir todas las competiciones ni los horarios del proveedor de TV; no inventar eventos. Para notificaciones automáticas hará falta un worker y opt-in explícito del usuario, separado de este PR.

## Pruebas locales

\`\`\`bash
PYTHONPATH=. python -m unittest tests.test_sky_sports -v
\`\`\`
