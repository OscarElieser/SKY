# SKY endurecido local

La pila endurecida está instalada y validada en Windows. Se inicia con:

```text
INICIAR_SKY_ENDURECIDO_WINDOWS.bat
```

Dirección HTTPS:

```text
https://127.0.0.1:8443/sky
```

Para detener todos sus procesos:

```text
DETENER_SKY_ENDURECIDO_WINDOWS.bat
```

## Arquitectura activa

- Caddy HTTPS y filtro de borde: `127.0.0.1:8443`.
- API FastAPI privada detrás del proxy: `127.0.0.1:18765`.
- Memurai compatible con Redis, autenticado y persistente: `127.0.0.1:16379`.
- Worker creativo separado del proceso HTTP.
- Secretos aleatorios en `.infra/run/secrets.json`, protegidos mediante ACL de Windows.
- Copias cifradas en `backups_hardened/`.
- Informes reproducibles en `security_reports/`.

## Validación ejecutada

- Suite: 223 pruebas superadas y 2 omitidas.
- Auditoría de dependencias: ninguna vulnerabilidad conocida detectada.
- Sonda dinámica: 9/9 controles superados.
- Límite distribuido: respuestas `429` confirmadas mediante Redis.
- Carga: 1,000/1,000 solicitudes HTTPS correctas, 183.34 solicitudes/s y p95 de 340.8 ms.
- Recuperación: 10 bases cifradas, verificadas y restauradas; la copia temporal fue eliminada después de comprobarla.

Esta configuración no abre puertos en el firewall ni publica SKY en Internet. Para cambiar de equipo o proveedor se reutilizan los mismos scripts y controles con el dominio y certificado de ese entorno.
