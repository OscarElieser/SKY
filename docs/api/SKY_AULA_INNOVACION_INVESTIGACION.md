# SKY Aula, Innovación e Investigación — funciones, fuentes y validación

**Rama:** feature/sky-docente-innovacion-20261023. **Estado:** desarrollo; no desplegado ni fusionado a main. SKY CORE continúa siendo la única asistente visible.

## SKY Docente

**Niveles:** educación inicial (MEIDI), primaria, secundaria/media, técnico/profesional, universitario, maestría y doctorado. Cualquier asignatura se puede organizar metodológicamente, pero el conocimiento especializado exige material, fuentes adecuadas y verificación.

**Siete momentos didácticos:** bienvenida/objetivo, conocimientos previos, explicación, ejemplo, práctica, reflexión y cierre. Distribución del tiempo según duración solicitada. Las clases se conservan en memoria por 90 minutos, sin recopilar calificaciones ni datos personales de estudiantes.

**Voz:** abrir /aula para iniciar, escuchar, silenciar y avanzar etapa por etapa. La narración usa las voces disponibles del navegador, cuando existan. El HUD de SKY también admite «SKY, impartí una clase de números naturales para primaria» y «SKY, siguiente paso de la clase» por voz, conservando su lesson_id durante la sesión. Si un equipo carece de voz, el texto sigue visible y SKY no asegura haber generado audio.

**Currículo oficial como referencia, no lectura verificada en cada petición:**
- MINED MEIDI: https://www.mined.gob.ni/educacion-inicial/
- MINED primaria: https://www.mined.gob.ni/educacion-primaria/
- MINED secundaria: https://www.mined.gob.ni/educacion-secundaria/
- INATEC: https://tecnacional.edu.ni/
- UNESCO IA y educación: https://www.unesco.org/es/articles/guia-para-el-uso-de-ia-generativa-en-educacion-e-investigacion

No atribuir una competencia, indicador o resultado a la edición oficial sin cotejo documental. Las clases son borradores docentes supervisados. Para personas menores de edad, no compartir datos identificables, grabaciones ni calificaciones mediante estas rutas. Requiere revisión docente humana.

## SKY Innovation Lab

**Eventos:** Rally Nacional Nicaragua Innova, Rally Latinoamericano de Innovación, Hackathon Nicaragua, INNOVATEC, emprendimiento, investigación aplicada y proyectos generales.

**Áreas:** educación, salud/medicina educativa, transporte, sociedad, medio ambiente, cultura, turismo, agropecuaria, tecnología, energía, vivienda, gestión pública, industria, economía y formación técnica.

**Entregables:** acta y roles, normas de equipo, árbol de problemas, objetivo general, SMART pendiente de indicadores reales, hipótesis, matriz impacto-viabilidad, propuesta de valor, buyer persona hipotético, mapa de empatía, Canvas de nueve bloques, MVP, plan de pruebas, pitch de 1–5 minutos y fuentes/limitaciones.

Los segundos asignados en el pitch son una estructura de ensayo, no una duración vocal ya verificada. El presupuesto, entrevistas, impacto y mercado permanecen como campos pendientes hasta que existan datos respaldados. No se inventan citas, usuarios, reconocimientos ni instituciones aliadas.

Fuentes de metodología para cotejar:
- INATEC Hackathon: https://mapa.tecnacional.edu.ni/hackathon-nicaragua
- Tecnológico Nacional: https://tecnacional.edu.ni/
- MINED y documentación curricular correspondiente.

Para medicina/salud, SKY es apoyo formativo y de investigación, nunca sistema de diagnóstico ni sustituto de revisión clínica.

## Investigación verificable

El módulo neural_core/sky_evidence_lab.py tiene:

1. **Evidence brief:** preguntas de investigación y fragmentos de la biblioteca privada cifrada del dueño, citados como sky-doc:... El documento aportado no se da por validado.
2. **Consulta oficial bajo solicitud expresa:** un máximo de cuatro fuentes preautorizadas MINED, INATEC, UNESCO u OMS, mediante HTTPS sin redirecciones y límites de respuesta. Devuelve URL, fecha UTC de consulta, SHA256 del contenido y extractos temáticos, o un estado de fallo.
3. **Comprobación de evidencia:** una fuente recuperada **no** prueba automáticamente una afirmación y no acredita publicación reciente, causalidad, ni un estudio científico revisado.

La investigación profunda automática con buscador abierto, revisión bibliográfica, DOI, datos actualizados, revisión cruzada de fuentes y referencias APA verificadas **sigue pendiente de desarrollo**. No declarar investigación académica completa a partir de una visita web o un enlace.

## Archivos profesionales

La API reutiliza SKY Office Studio para producir Word (DOCX), PowerPoint (PPTX), PDF y Markdown de las clases y propuestas. Los archivos son reales pero contienen borradores sujetos a revisión metodológica, factual y visual. Los encabezados incluyen X-SKY-Research-Status: draft-not-externally-verified.

## Endpoints de la API privada

Requieren clave X-SKY-KEY y segundo factor cuando está habilitado.

- GET /api/sky/academy/capabilities — catálogo y límites
- GET /api/sky/academy/education/levels — niveles
- POST /api/sky/academy/education/lesson — plan didáctico
- POST /api/sky/academy/education/sessions — iniciar clase
- GET /api/sky/academy/education/sessions/{id} — consultar momento
- POST /api/sky/academy/education/sessions/{id}/next — avanzar
- DELETE /api/sky/academy/education/sessions/{id} — cerrar
- POST /api/sky/academy/education/lesson/document — exportar clase
- GET /api/sky/academy/innovation/capabilities — metodología
- POST /api/sky/academy/innovation/project — Canvas, pitch, evidencias
- POST /api/sky/academy/innovation/project/document — exportar propuesta
- POST /api/sky/academy/research/brief — brechas y evidencia privada
- GET /api/sky/academy/research/sources — catálogo oficial
- POST /api/sky/academy/research/official-sources — recuperar hasta 4 portales oficiales

Ejemplo de clase: topic="Números naturales: antecesor y sucesor", level="inicial", grade="tercer nivel", duration_minutes=45, learning_goal="Relaciona anterior y posterior hasta el 20".

Ejemplo de proyecto: name="Movilidad educativa", challenge="Estudiantes rurales reportan dificultades de transporte para llegar a sus centros educativos", category="transporte", event="hackathon_nicaragua", solution="Prototipo colaborativo de horarios", pitch_minutes=3. Los datos del ejemplo son supuestos, no resultados de una encuesta.

## Seguridad, privacidad y comprobación

La API comparte la autenticación original del dueño; ninguna solicitud permite ejecutar comandos arbitrarios. No introducir datos de pacientes, estudiantes identificados ni secretos en proyectos sin un proceso explícito de privacidad.

Pruebas incluidas: tests/test_sky_academy_innovation.py (siete niveles, momentos, voz y continuidad, eventos, Canvas, fuentes oficiales simuladas, rechazo de URL no autorizada, fallos web honestos, exportaciones Office). Se añadieron a CI Windows/Linux; hace falta revisar el SHA final y probar voz, contenidos y formato en equipo real.

## Pendientes para SKY Docente avanzada

- Motor de razonamiento didáctico local que explique conceptos originales sobre fuentes verificadas.
- Tutor con preguntas y evaluación formativa a partir de respuestas, sin almacenar datos de menores sin consentimiento.
- Bancos de ejercicios con verificadores reales de matemáticas, física, química y programación.
- Accesibilidad, inclusión y adaptación curricular por edición.
- Investigación científica profunda con recuperación de papers, DOI y citas contrastadas.
- Integración multimedia real de imágenes, demostraciones y videos, revisados antes de usarse en el aula.
- Validación humana y pedagógica antes de declarar la plataforma lista para aulas profesionales.

**Esta PR debe permanecer en borrador:** depende de PR14 y otras ramas previas; no fusionar a main sin CI verde, auditoría de seguridad y comprobaciones físicas.
