# Organización oficial del repositorio SKY IA

Estado: estructura objetivo y reglas de mantenimiento, **no migración completada**.

## Directorios principales (mantener rutas existentes)

| Ruta | Responsabilidad |
| --- | --- |
| `mobile/android-agent/` | Aplicación Android, Kotlin, Gradle, pruebas y documentación móvil |
| `neural_core/` | Lógica del núcleo Windows/Python, políticas, memoria y orquestación |
| `metaverse/` | API FastAPI, endpoints y HUD de escritorio |
| `shared/` | Contratos y esquemas compartidos entre plataformas, sin credenciales |
| `tests/` | Pruebas Python y regresiones de seguridad/paridad |
| `.github/workflows/` | Compilaciones, análisis y pruebas CI |
| `docs/` | Arquitectura, procedimientos, evidencias y decisiones |
| `scripts/` | Automatizaciones de desarrollo existentes, cuando corresponda |

## Convenciones

1. Un solo producto SKY, ejecutores nativos independientes; no forzar dependencia Android→Windows.
2. Toda nueva función compartida debe declarar intención, adaptador, autorización y recibo verificable.
3. Código Android dentro de `mobile/android-agent/`; código del núcleo Windows dentro de `neural_core/` o sus integraciones actuales.
4. Mantener contratos en `shared/` y pruebas de compatibilidad en `tests/`.
5. Nuevos documentos: `docs/arquitectura/` para diseño, `docs/` para informes existentes; no reubicar documentos antiguos sin actualizar enlaces.
6. Evitar archivos generados, APK, secretos, bases privadas, `.env` y claves en el repositorio. Los binarios de distribución van en GitHub Releases/artefactos CI.
7. Toda reorganización de rutas se hace por lotes pequeños, actualizando importaciones, scripts, enlaces, workflows y pruebas **antes** de eliminar la ruta antigua.
8. Nunca eliminar funcionalidades, historial ni módulos sin una migración reversible y evidencia de pruebas.
9. La presencia de un archivo o una prueba estática no certifica el comportamiento en Windows/Samsung.

## Plan de ordenamiento sin interrupciones

- **Etapa A:** inventariar directorios y dependencias, mantener rutas actuales; establecer este mapa.
- **Etapa B:** añadir controles automáticos de ubicación de archivos y protección contra secretos; verificar en Linux y Windows.
- **Etapa C:** agrupar documentación histórica por temática con redirecciones/enlaces actualizados.
- **Etapa D:** refactorizar módulos duplicados únicamente con pruebas de integración y reversión.
- **Etapa E:** validar compilación Android, ejecución Windows y dispositivos físicos.

## Contratos y aceptación

- [Contrato de seguridad](../../shared/sky_core_contract_v1.json)
- [Inventario de paridad](../../shared/sky_platform_parity.json)
- [Informe Windows/Android](../SKY_WINDOWS_ANDROID_PARITY_2026-10-29.md)
- [Pruebas de paridad](../../tests/test_sky_platform_parity.py)

**Importante:** este documento no afirma que la reorganización física ni la paridad funcional estén terminadas.
