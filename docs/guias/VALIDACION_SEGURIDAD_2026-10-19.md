# Validación de seguridad e infraestructura — 2026-10-19

## Resultado local

- Suite completa: **223 pruebas superadas y 2 omitidas**.
- Compilación de los módulos críticos: correcta.
- Auditoría de dependencias instaladas con `pip-audit 2.10.1`: **sin vulnerabilidades conocidas detectadas** en esta fecha.
- Preflight local: módulos y bases SQLite operativos e íntegros.
- Los ocho iniciadores de Windows contienen comandos válidos; ninguno permanece vacío.
- La API y Streamlit continúan enlazados exclusivamente a `127.0.0.1`.

## Controles reforzados

- El modo `public` exige ahora una `SKY_API_KEY` explícita de al menos 32 caracteres. No puede depender del token local generado en disco.
- La clave de API y el secreto MFA deben ser distintos.
- Continúan siendo obligatorios para el arranque público: dominio permitido explícito, MFA TOTP, Redis disponible, proxy TLS verificado y worker creativo separado.
- El preflight informa el estado de despliegue y termina con error si una configuración pública no satisface esos requisitos.
- CI audita dependencias y ejecuta las pruebas de seguridad, despliegue, respaldo y recuperación de v10.1 a v10.5.

## Bloqueos observados

El escáner de publicación rechazó correctamente el árbol de trabajo actual porque contiene `.env` con credenciales y una base SQLite privada bajo `data/`. Estos archivos son válidos para operación local, pero **no deben copiarse a una publicación, imagen o repositorio**. El escáner no imprime el valor de las credenciales.

## Pendiente antes de usuarios públicos

SKY permanece **no certificado para exposición pública**. Todavía se requieren fuera del repositorio:

1. Proxy HTTPS real con IPs de proxy confiables, WAF y mitigación DDoS comprobados.
2. Redis privado desplegado, autenticado, respaldado y sometido a pruebas de caída.
3. Gestión externa de secretos, rotación y procedimiento seguro de recuperación MFA.
4. Ensayo de carga y concurrencia con objetivos de capacidad definidos.
5. Restauración ensayada con una copia operativa completa guardada fuera del servidor.
6. Auditoría de registros resistente a manipulación y alertas operativas.
7. Prueba de penetración independiente y revisión de privacidad/retención de datos.

Hasta cerrar esos puntos, mantener `SKY_DEPLOYMENT_MODE=local` y no escuchar en `0.0.0.0`.
