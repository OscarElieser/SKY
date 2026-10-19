# SKY IA v10.4 — Inicio, seguridad y recuperación

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán. Los derechos concretos del software y sus dependencias se rigen por sus licencias.

## Instalar

1. Descomprimí el ZIP en una carpeta nueva. Conservá la versión anterior y respaldá `local_data`, archivos y `.env` antes de migrar.
2. Instalá Python y los requisitos de SKY: `python -m pip install -r requirements_studio.txt`, además de los requisitos de las funcionalidades adicionales que uses. FFmpeg y eSpeak son opcionales del sistema para video y narración local.
3. Iniciá SKY con `INICIAR_SKY_V9_WINDOWS.bat` (Windows) o `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765`.
4. Accedé localmente a `http://127.0.0.1:8765/sky`. Herramientas avanzadas dentro de **Espacios**; BAQUEANO solo para quien tenga credenciales del creador.

## Crear un respaldo **cifrado** de bases de datos

En una terminal local, establecé `SKY_BACKUP_PASSPHRASE` a una contraseña larga y privada (mínimo 16 caracteres). Evitá incluirla en un comando que quede en el historial, en GitHub o en archivos de proyecto. Se recomienda solicitarla de manera interactiva en el sistema operativo o utilizar un gestor local de secretos que la establezca como variable de entorno.

```bash
python -m neural_core.sky_secure_backup create --file /ruta/privada/SKY_2026.skybackup
python -m neural_core.sky_secure_backup verify --file /ruta/privada/SKY_2026.skybackup
```

- La primera operación guarda una instantánea consistente de las bases SQLite inicializadas. El archivo **no** puede sobrescribirse si existe.
- La segunda comprueba autenticidad e integridad, y restaura cada SQLite **en memoria para una comprobación**. No escribe en las bases del usuario.
- Ninguna de las operaciones necesita conexión a Internet.
- El archivo está cifrado con AES-256-GCM; se deriva la clave mediante scrypt, con sal y nonce aleatorios. No contiene la frase de acceso.
- **No olvidés respaldar medios, documentos, configuración, MFA y claves por un procedimiento separado**, cifrado y verificado. El fichero `.skybackup` *no* incluye esas clases de archivos.

## Idiomas y voz

Abrí el selector de idioma de SKY. Los textos estáticos revisados se aplican en diferentes vistas, incluido el contenido accesible `aria-label` y títulos estáticos. El usuario puede recuperar el idioma anterior inmediatamente. Las conversaciones y archivos personales **no** se envían a motores de traducción salvo autorización explícita.

`GET /api/i18n/coverage` requiere clave privada y muestra cobertura verificada por idioma. La voz local usa las voces eSpeak instaladas. SKY no tiene reconocimiento completo en 90 idiomas ni doblaje profesional con voces naturales para todas las lenguas.

## Verificación técnica

```bash
PYTHONPATH=. pytest -q
node --check metaverse/static/sky-global-i18n.js
python -m compileall -q neural_core metaverse
```

Probado en el entorno de desarrollo: **214 pruebas superadas**. Las dependencias, idiomas y hardware disponibles en otros equipos pueden variar.

## Producción

**No expongás el puerto 8765 a Internet directamente.** SKY requiere identidad fuerte y MFA obligatorio para propietarios, terminación TLS y proxies de confianza, separación de procesos FFmpeg, Redis privado para límites distribuidos, almacén seguro de secretos, restauración completa de datos y archivos, observabilidad y auditorías externas. `SKY_DEPLOYMENT_MODE=public` está diseñado para fallar al iniciar si faltan varias condiciones indispensables, pero **no** equivale a certificación.

Repositorio maestro: https://github.com/OscarElieser/SKY.
