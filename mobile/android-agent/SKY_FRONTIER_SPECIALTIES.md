# SKY IA Android · Frontera científica y seguridad supervisada

Fecha: 2026-10-30. Esta fase modifica únicamente `mobile/android-agent`. La rama Windows **no se modifica**.

## Integración sin botones

Se añade `SkyFrontierSpecialties.kt` con **42 especialidades consultivas** que complementan las **33 familias** anteriores de `SkyExpertRoles.kt`. El reconocimiento ocurre automáticamente desde el mismo panel de voz y texto de SKY. Una consulta puede recibir orientación de distintas disciplinas, pero **no activa un ejecutor con permisos ilimitados**.

Las 42 especialidades se distinguen en cuatro modos:

- **RESEARCH:** conceptos, metodologías, revisiones científicas y fuentes comprobables. No inventar publicaciones ni resultados.
- **SIMULATION:** describir y, solo con una herramienta validada, ejecutar modelos físicos, matemáticos o informáticos con parámetros y unidades.
- **DEFENSIVE:** revisión de seguridad, auditoría de código, privacidad, detección y recuperación exclusivamente sobre activos propios o autorizados; sin funciones de intrusión ni exfiltración.
- **SPECULATIVE:** hipótesis, investigación emergente, ciencia ficción y conceptos que no corresponden a tecnología comprobada. No afirmar efectos físicos imposibles ni capacidades ficticias.

Las etiquetas son **rutas de respuesta**, no sustituyen hardware, software científico o capacidades ya conectadas.

## Primeras herramientas científicas reales

`SkyScientificCalculator.kt` calcula con fórmulas y unidades del SI, localmente, **sin pedirle al LLM que invente números**:

- «SKY, calcula energía cinética masa 2 kg velocidad 3 m/s» → `9.000 J` con `E = ½mv²`
- «SKY, calcula fuerza resultante masa 5 kg aceleración 2 m/s2» → `10.000 N` con `F = ma`
- «SKY, calcula ley de Ohm resistencia 4 ohmios corriente 3 amperios» → `12.000 V` con `V = IR`

La app devuelve las condiciones necesarias si faltan datos; no presupone cantidades. Esto representa **tres cálculos verificables**, no un motor FEA, simulador de tokamak, ordenador cuántico ni sistema de robótica.

## Segundo bloque: estadística y álgebra, ejecutadas en Android (0.8.37 en validación)

Este bloque agrega **dos herramientas matemáticas reales adicionales**, sin botones ni conexión obligatoria. La ejecución ocurre **antes de delegar el mensaje a modelos de lenguaje**; si faltan parámetros, SKY pide datos y no supone valores.

| Orden oral o escrita | Operación verificable | Resultado de referencia |
| --- | --- | --- |
| «SKY, calcula promedio de 2, 4 y 6» | media, mediana, rango, varianza y desviación estándar poblacional, cálculo Welford + comprobación independiente | media 4, mediana 4, varianza 2.6667, desviación 1.6330 |
| «SKY, calcula mediana de -2, 3.5, 7, 12» | medianas y estadística descriptiva sobre datos proporcionados | mediana 5.25 |
| «SKY, resuelve ecuación cuadrática a=1 b=-3 c=2» | solución de ax²+bx+c=0 con manejo de cancelación numérica | raíces 1 y 2 |
| «SKY, resuelve ecuación cuadrática a=1 b=0 c=1» | raíces complejas si el discriminante es negativo | ±1i |

Módulos: `SkyStatisticsCalculator.kt`, `SkyQuadraticSolver.kt`; pruebas: `SkyStatisticsCalculatorTest.kt`, `SkyQuadraticSolverTest.kt`. Los cuatro cálculos anteriores de ejemplo son **resultados matemáticos esperados**, no evidencia de ejecución en tu Samsung: para eso deben pasar CI y las pruebas físicas.

**Restricciones demostrables:** la estadística acepta 2–100 valores finitos explícitos, punto para los decimales, y determina la **varianza poblacional (N)**, no la muestral. La ecuación cuadrática exige coeficientes `a,b,c`, `a ≠ 0`, con rango numérico limitado. No se sustituyen calculadores de ingeniería, medicina, criptografía ni sistemas físicos. El código no tiene interfaces para enviar mensajes, pagar, controlar equipos o ejecutar scripts.

**Validación pendiente:** JUnit + compilación Android, emuladores 15/16, APK firmada y prueba en Samsung con voz, texto, modo avión, error de datos, permisos y bloqueo de pantalla. No dar por terminada la distribución hasta que se cumplan.

## Ingeniería y seguridad

Control humano: `interpretar → planificar → seleccionar herramienta → autorizar acción sensible → ejecutar → recibir prueba → reportar`. Ningún rol nuevo obtiene acceso a contactos, micrófono, red, datos médicos, drones o apps de terceros por el simple hecho de ser registrado.

No se incorporaron generadores de ataques polimórficos, interceptores de comunicaciones ajenas, exploits para infraestructuras críticas, mecanismos de robo de credenciales, ataques a sensores humanos, sabotaje de energía ni mutadores ofensivos. Se encauzan temas de seguridad a **auditoría defensiva** y simulaciones inocuas y consentidas.

En dominios físicos, médicos, químicos, nucleares y aeroespaciales hace falta metodología y validación especializada. Los conceptos como manipulación de leyes del universo, hacker de líneas temporales y lectura de pensamientos sin sensores se tratan como **especulación, nunca como capacidades operativas de SKY**.

## Evidencia de calidad y pendientes

### Ya en código
- [x] Registro de 42 especialidades con modos y salvaguardas.
- [x] Ruteo automático por voz y texto junto a las 33 familias anteriores.
- [x] Calculadora de tres ecuaciones del SI con parámetros explícitos.
- [x] Casos de prueba JUnit para clasificación, salvaguardas y resultados.
- [x] Sin añadir botones, permisos o servicios de Android.

### Requiere pruebas
- [ ] CI: compilar Android y ejecutar pruebas unitarias.
- [ ] Emuladores Android 15/16, firma APK y publicación de una versión nueva.
- [ ] En Samsung, dictado real de los tres cálculos y comprobación de que SKY no exige clave de nube.
- [ ] Medir precisión, voz y comportamiento ante datos faltantes o unidades incorrectas.

### Ampliaciones futuras, no terminadas
- [ ] Verificador simbólico con biblioteca matemática acreditada y evaluación de unidades.
- [ ] Integración con simuladores físicos/moleculares especializados y entornos aislados.
- [ ] Laboratorios virtuales y simulaciones docentes exportables.
- [ ] Análisis de código con pruebas reproducibles y escáneres defensivos autorizados.
- [ ] Modelos locales optimizados para la memoria, CPU/GPU/NPU real del Samsung.
- [ ] Versionado de aprendizajes, corpus con procedencia, evaluación contra alucinaciones y rollback.
- [ ] Gestión real de investigación con citas, DOI y lectura de trabajos de forma permitida.
- [ ] Verificar cada herramienta especializada antes de presentar el rol como «funcional».

## Referencias del repositorio
- `SkyExpertRoles.kt` — 33 familias generales.
- `SkyFrontierSpecialties.kt` — 42 especialistas de frontera, consultivos.
- `SkyAndroidCognition.kt` — selección automática y guía.
- `SkyScientificCalculator.kt` — ecuaciones deterministas, sin red.
- `SkyScientificCalculatorTest.kt`, `SkyFrontierSpecialtiesTest.kt` — pruebas.
- `SKY_JARVIS_MULTIRROL_33.md` — arquitectura del núcleo anterior.

**Una sola SKY con funciones reales verificables; no declarar una APK lista hasta comprobar sus workflows.**
