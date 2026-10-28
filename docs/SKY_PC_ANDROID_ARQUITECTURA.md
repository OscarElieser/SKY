# SKY IA — Arquitectura coordinada Windows + Android

## Objetivo
Un solo proyecto SKY y una sola rama oficial **main**, con aplicaciones
separadas por plataforma y conectadas a través de una API propia.
No se debe copiar el agente Windows dentro de una APK ni borrar módulos
existentes para añadir funciones móviles.

```text
github.com/OscarElieser/SKY  (rama main)
│
├── neural_core/                  IA, memoria y servicios compartidos
├── metaverse/                    FastAPI, HUD y rutas seguras SKY Core
├── agente_dispositivo.py         Acciones y permisos del dispositivo Windows
├── mobile/
│   └── android-agent/
│       ├── app/                  Código Kotlin y permisos de Android
│       ├── apk/                  Carpeta exclusiva de APK de prueba (en CI)
│       │   ├── README.md
│       │   └── .gitignore
│       └── README.md             Uso y configuración del celular
├── tests/                        Pruebas del backend y autorizaciones
└── .github/workflows/
    └── sky-mobile-agent.yml      Verifica Python, compila Android, genera APK
```

## Comunicación real disponible
1. Windows inicia SKY Core y expone **una URL HTTPS privada**, con acceso
   controlado mediante túnel seguro o red privada. Nunca publicar la API
   sin autenticación.
2. En el panel del propietario se genera un código efímero para enlazar
   Android. La aplicación almacena el token de dispositivo cifrado con
   Android Keystore. No recibe `SKY_API_KEY`.
3. El chat Android requiere **autorización independiente de 24 h**.
   Envia mensajes por `/api/sky/mobile-chat/chat` y muestra/lee respuestas
   del SKY Core. La memoria del núcleo puede utilizarse conforme a la
   implementación del backend; la pantalla móvil conserva únicamente un
   historial de interfaz limitado, que no es una sincronización completa
   del historial de Windows.
4. Para abrir aplicaciones permitidas se usa la cola
   `/api/sky/mobile-agent/...` y confirmación explícita en el teléfono.
5. Las funciones del dispositivo Windows siguen sujetos a las políticas
   y permisos del agente de Windows: el teléfono no las hereda automáticamente.

## Separación de responsabilidades

| Elemento | Computadora | Celular |
| --- | --- | --- |
| Interfaz | SKY HUD | SKY IA, ojos animados, voz y chat nativo |
| Herramientas locales | Agente Windows | Acciones Android autorizadas |
| Motor y proveedores IA | SKY Core; local/nube si configurado | Consulta SKY Core por HTTPS |
| Identidad | Autenticación del propietario + MFA | Token de dispositivo y token de chat limitados |
| Archivos locales | Acceso condicionado por políticas del PC | Solo permisos Android concedidos |
| Entregable | Instaladores/ejecutables Windows | APK independiente en `mobile/android-agent/apk/` |

## Niveles de disponibilidad

- **Comprobado por CI**: compilación Android y pruebas de backend en cada
  modificación relacionada. Un resultado en verde certifica las tareas del
  workflow, **no** la compatibilidad en cada Samsung.
- **Depende de la PC**: cuando SKY Core solo corre en la computadora,
  apagarla interrumpe la conversación Android aunque la aplicación abra.
- **Pendiente**: servicio remoto para IA sin PC, sincronización persistente
  y consentida de memoria/historial, comandos multiplataforma verificables,
  activación por voz con pantalla bloqueada dentro de las restricciones
  del sistema operativo, y firma APK estable para actualizaciones.

## Reglas de integración
- Conservar módulos actuales y no alterar permisos silenciosamente.
- Mantener un único contrato de API versionado y validar los endpoints
  existentes antes de ampliar Android.
- Identificar el origen de la acción (`windows` o `android`) y exigir
  autorización del dispositivo de destino.
- Nunca guardar contraseñas, tokens, bases privadas ni APK firmadas de
  producción en Git.
- Emparejamiento y credenciales en Ajustes, no en la pantalla principal.
- Confirmar una tarea mediante evidencia del dispositivo, no confundir
  "orden enviada" con "acción completada".
- Subir código fuente y documentación a `main`; entregar APK de desarrollo
  como artefacto del workflow en GitHub.
