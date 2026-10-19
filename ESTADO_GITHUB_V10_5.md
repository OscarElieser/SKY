# Publicación SKY IA v10.5 en GitHub

Repositorio central: `https://github.com/OscarElieser/SKY`.

El código se publica sobre `main` mediante un commit normal con los archivos de v10.5, conservando todos los módulos anteriores. No deben subirse archivos `.env`, `local_data/`, SQLite privadas, tokens, claves MFA ni modelos de voz descargados.

Las versiones históricas siguen identificadas por el historial del repositorio, sus ramas o archivos ZIP conservados. La disponibilidad de todas las versiones como **GitHub Releases** debe comprobarse por separado y no se presume.

Después de publicar, verificar el SHA del commit y que los módulos `sky_recovery_full.py`, `sky_stt_local.py`, `sky_i18n_v105.py`, `stt_v105_api.py`, la suite de pruebas y los docs estén presentes.
