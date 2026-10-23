# SKY IA v10.9 — Infraestructura integral y verificación multilingüe

**Visión y autoría conceptual del proyecto:** Oscar Elieser Chamorro Guzmán.

## Cambios efectivamente implementados

1. **Pila Docker integral de prueba** (`deploy/compose.integration.yml`): Caddy HTTPS con CA local para CI, Redis autenticado, API con MFA y clave desde archivo, y renderizador sin acceso a red. El puerto TLS de prueba está ligado **solo a 127.0.0.1**; API y Redis no publican puertos.
2. **Pruebas HTTP y TLS verificables** (`scripts/ci_stack_smoke_v109.sh`): verifican cadena y hostname del certificado con `curl --cacert`, 401 de API privada sin clave, salud de Redis, cuatro servicios levantados y ausencia de rutas de red en renderizador.
3. **Restauración cifrada en contenedor independiente** (`scripts/cross_host_recovery_v109.py`, `scripts/ci_cross_container_v109.sh`): verifica una huella SHA-256 obtenida por separado, autentica AES-GCM, reconstruye datos SQLite y medios sintéticos fuera de la instalación principal, con contenedor sin red y sistema de archivos raíz de solo lectura.
4. **Banco de voz auténtico preparado en Actions**: el job de GitHub instala `faster-whisper` en un runner, descarga un modelo abierto pequeño solo para CI, crea tres locuciones sintéticas ES/FR/EN y **mide** tasa de error WER sobre las transcripciones reales. No entrega los pesos, audios ni transcripciones. El job solo cuenta como prueba REAL cuando GitHub confirma su ejecución.
5. **Idiomas**: nueve textos breves de operación en nueve idiomas, incorporados al glosario común; las traducciones restantes se siguen contabilizando como incompletas.
6. **Regresión por grupos**: conserva las pruebas de v10.8, sin sobreescribir los proyectos anteriores ni tocar BAQUEANO.

## Resultados y límites

- En entorno local sin Docker y sin modelo STT, la auditoría estática, la recuperación cifrada y las pruebas de lógica se ejecutan. **La pila Docker real, el modelo Whisper real y el servidor remoto deben verificarse en sus respectivos entornos.**
- El runner CI con Docker es un host independiente efímero, **no un segundo servidor del usuario**. El script de transferencia no realiza conexiones SSH ni reemplaza instalaciones activas.
- `deploy/compose.integration.yml` es para ensayos, no producción. `deploy/compose.yml` sigue siendo el ejemplo de producción sujeto a auditoría.
- Esto NO es una certificación pública, prueba de penetración externa, ni garantía de reconocimiento de 90 idiomas.
