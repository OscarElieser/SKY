# SKY v9.9 — Acta técnica de validación local

- Paquete anterior v9.8: 180 pruebas automatizadas.
- Versión v9.9: 183 pruebas automatizadas superadas.
- Nueva prueba: selección GrabCut con puntos que deben conservarse y excluirse, con control de acceso y rechazo de coordenadas inválidas.
- Nueva prueba: MP4 real renderizado por FFmpeg con 4 fotogramas de texto e interpolación suave; duración verificada mediante FFprobe; exportación y reimportación editable `.skyzip`.
- Nueva prueba: rechazo de tiempos desordenados, fuera del clip e interpolación no admitida.
- JavaScript del editor: `node --check` sin errores.
- Gemini en vivo: no probado por ausencia de clave real en la sesión.
- Seguimiento de objetos y rotoscopia: no implementados.
- Producción pública: no certificada.
