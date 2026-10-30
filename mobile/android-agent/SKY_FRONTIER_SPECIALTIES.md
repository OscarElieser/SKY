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
