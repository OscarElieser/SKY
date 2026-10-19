# SKY Sports Center — Real Madrid (módulo opcional)

La personalidad deportiva de SKY celebra al Real Madrid, pero **no manipula hechos, fuentes ni probabilidades**. Ofrece pronósticos orientativos (Poisson básico), agenda, noticias y acceso a operadores oficiales. No promueve apuestas.

## Configuración

1. Obtené una clave personal en https://www.football-data.org/ y guardala en el archivo local \`.env\`, **nunca en Git**:
   \`SKY_FOOTBALL_DATA_TOKEN=tu_clave\`.
2. Ejecutá la interfaz Streamlit habitual y abrí **⚽ SKY Sports Center**.
3. Consultá "Próximo partido", "Pronóstico experimental" o escribí la orden de voz/texto \`SKY, muéstrame el partido en vivo de Madrid\`.
4. La orden **no** se ejecuta sin intención explícita; consulta estado actual y muestra enlace oficial solo si la API confirma partido en directo. El operador requiere autorización, región y, generalmente, suscripción. Algunos contenidos no ofrecen reproducción incrustada: en ese caso se abrirá la página oficial.

## Derechos audiovisuales

La guía orientativa para Nicaragua usa:
- LaLiga: ViX Premium / Sky Sports, según derecho y plan disponibles.
- Champions League: ESPN figura como operador regional de Centroamérica según UEFA.

Ningún enlace de terceros del tipo Fútbol Libre se utiliza para extraer reproductores, tokens o señales. No se ofrecen proxies de TV, DRM bypass ni retransmisiones sin licencia.

## Fuentes y límites

- [football-data.org v4](https://docs.football-data.org/general/v4/coding_client.html): resultados y partidos. La cobertura y cuotas dependen del plan del usuario.
- [LaLiga, operadores oficiales](https://www.laliga.com/es-US/donde-ver-laliga-easports).
- [UEFA, canales oficiales](https://www.uefa.com/uefachampionsleague/news/0253-0d82037aaedd-f371c464f919-1000--where-to-watch-the-uefa-champions-league-tv-broadcast-partne/).

La interfaz realiza consultas solo al pulsar botones o dar comandos; no se inicia streaming en segundo plano. Para notificaciones automáticas hará falta un worker y opt-in explícito del usuario, separado de este PR.

## Pruebas locales

\`\`\`bash
PYTHONPATH=. python -m unittest tests.test_sky_sports -v
\`\`\`
