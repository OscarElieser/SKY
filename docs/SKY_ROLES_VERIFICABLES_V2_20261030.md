# SKY IA — Ejecución científica, docente y autocorrección limitada (30/10/2026)

Este bloque amplía **la API propia** sin sustituir SKY Windows, SKY Android,
Workflows, permisos existentes o la memoria cifrada.

## Capacidades añadidas con código ejecutable
- fisica/mecanica_si: cinemática de aceleración constante, energía cinética y
  segunda ley de Newton. Entradas y salidas con nombres explícitos de unidades SI.
- quimica/masa_molar: composiciones neutras con paréntesis, 32 elementos
  disponibles y masas atómicas redondeadas. **No** interpreta todas las
  fórmulas químicas ni reemplaza RDKit o investigación de laboratorio.
- educacion/evaluar_rubrica: calcula puntuaciones a partir de criterios
  proporcionados, valida máximos y duplicados. Los niveles son orientativos
  de SKY, no una escala oficial de MEIDI/INATEC.

Nuevos roles figuran en GET /api/sky/verified-roles/catalog y utilizan el
mismo POST /api/sky/verified-roles/run. Ejemplo:

{
  "steps": [
    {"id":"fisica","role":"fisica","tool":"mecanica_si",
      "args":{"modelo":"segunda_ley_newton","masa_kg":3,"aceleracion_m_s2":4}},
    {"id":"matematicas","role":"matematicas","tool":"calcular",
      "depends_on":"fisica","args":{"expression":"fuerza_n * 2"}}
  ]
}

Resultado: 12 N y cálculo posterior 24, dentro de su alcance exacto.
El sistema no modifica documentos o aplicaciones y no obtiene permisos nuevos.

## Bucle de revisión y recuperación

Para operaciones locales puras, el revisor compara la salida con controles
numéricos/recalculos. En caso de discordancia, repite **una sola vez** la misma
operación. Si sigue incorrecta, falla y bloquea el resto del plan. Las
respuestas de investigación externa no se reintentan ni se declaran verificadas.

Esto es re-ejecución limitada de cálculo, **no** autocorrección de código
generado, aprendizaje de pesos, autoprogramación general ni autoconciencia.

Las métricas solo guardan nombre de rol/herramienta, estado final y duración,
sin registrar texto privado ni secretos.

## Criterio de aceptación

CI ejecuta test_sky_verified_*.py (tres suites). Se comprueban conversiones
matemáticas, datos de química, rúbricas, bloqueo de entradas inválidas, cadenas
entre roles, un error recuperable y un error persistente detenido.

El núcleo de Windows y el APK de Android **no** están certificados por estas
pruebas de Python. Su uso requiere servidor actualizado y cliente conectado.
