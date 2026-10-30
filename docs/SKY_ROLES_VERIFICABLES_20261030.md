# SKY — Primer bloque de roles verificables (30/10/2026)

Este bloque es funcional, acotado y aditivo; no sustituye el código existente de
SKY Windows, SKY Android, el Supervisor ni el sistema de permisos.

## Herramientas reales
- matematicas/calcular: AST restringido y segunda comprobación.
- datos/resumen: estadísticas reales sobre datos suministrados.
- programacion/sintaxis_python: analiza sintaxis, sin ejecutar el código.
- ciberseguridad/auditoria_python: patrones AST acotados, NO auditoría completa.
- investigacion/semantic_scholar: conector externo ya existente; exige consentimiento
  allow_network=true. Sus referencias siguen NO VERIFICADAS.

Los demás roles del catálogo permanecen explícitamente como catalogue_only, nunca
se declaran operativos por su nombre. Se ampliarán conectando herramientas reales,
pruebas y permisos propios.

## API propia autenticada
GET /api/sky/verified-roles/catalog
GET /api/sky/verified-roles/metrics
POST /api/sky/verified-roles/run

Ejemplo de colaboración medible:

{
  "allow_network": false,
  "steps": [
    {"id":"stats","role":"datos","tool":"resumen","args":{"values":[2,4,6]}},
    {"id":"calc","role":"matematicas","tool":"calcular",
     "depends_on":"stats","args":{"expression":"mean * 3"}}
  ]
}

VERIFIED_LIMITED_SCOPE verifica solamente la operación local declarada;
REQUIRES_SOURCE_VERIFICATION exige revisión de fuentes y FAILED bloquea los
siguientes pasos. No existe ejecución autónoma de shell, cambios en archivos de
usuarios, acceso a apps o entrenamiento de pesos del modelo.

## Memoria, auditoría y evolución

SQLite local almacena únicamente metadatos por rol (tipo, estado, duración),
no prompts, códigos ni credenciales. Se puede medir la tasa de fallos de
herramientas y usar esos datos en un proceso posterior de mejoras con revisión.
El entrenamiento de pesos y un loop de autocorrección en sandbox requieren
hardware, infraestructura y pruebas independientes.

## Pendiente antes de declarar el ecosistema completo
Integrar especialidades de docencia, física, química, ciencia de datos avanzada
y medios; añadir pruebas de integración con SKY Android y Windows físicos;
aislar ejecución real de código en contenedores con recursos limitados; habilitar
acciones de riesgo exclusivamente por Workflows autorizado; documentar métricas
de latencia, disponibilidad y calidad.

Verificación automática: .github/workflows/sky-verified-roles.yml
