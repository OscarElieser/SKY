# SKY v12.6 en Windows: instalación, PIN, arranque y reversión (PowerShell)

Todos los comandos se ejecutan en **PowerShell, sin permisos de administrador**, dentro de la carpeta donde clonaste SKY. En los ejemplos esa carpeta es `$SKY`; ajustá la ruta a la tuya.

```powershell
$SKY = "$env:USERPROFILE\SKY"      # ← cambiala si clonaste SKY en otro lugar
Set-Location $SKY
```

## 1. Traer la versión v12.6 (rama de revisión)

```powershell
git fetch origin
git status                         # anotá si tenés cambios locales: no se pierden, pero conviene guardarlos
git stash push -m "antes de v12.6" # sólo si `git status` mostró cambios
git checkout sky-v12.6-fiabilidad
```

Cuando el PR se fusione a `main`, usá `git checkout main; git pull`.

## 2. Instalar o actualizar dependencias

No hay dependencias nuevas: `psutil` ya estaba en `requirements.txt` y el instalador ya lo instalaba. El instalador se puede ejecutar varias veces y salta lo que ya está.

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar_sky.ps1            # o doble clic en INSTALAR_SKY_WINDOWS.bat
powershell -ExecutionPolicy Bypass -File .\instalar_sky.ps1 -Siempre   # además: arranca con Windows y no se suspende enchufado
```

Al final, el instalador ofrece configurar el PIN.

## 3. Configurar el PIN del dueño (sólo en tu equipo)

```powershell
.\.venv\Scripts\python.exe sky_pin.py configurar     # el PIN se escribe sin eco; nunca lo pases como argumento
.\.venv\Scripts\python.exe sky_pin.py estado
```

- Usá de 6 a 12 dígitos, ni repetidos ni consecutivos.
- Sólo se guarda un verificador scrypt en `%USERPROFILE%\.neuralt\sentinel.json`.
- **Para desbloquear por voz,** decí los dígitos de a uno: «cuatro, siete, dos…». Por escrito, en la interfaz.
- **Volver a bloquear:** decí «SKY, bloquéate», escribilo, usá el botón «Bloquear SKY» del Security Center o ejecutá `.\.venv\Scripts\python.exe sky_pin.py bloquear`.
- **Si olvidaste el PIN:** `.\.venv\Scripts\python.exe sky_pin.py restablecer`. Hay que escribir `RESTABLECER` para confirmar. No toca tu memoria, tus permisos ni tu historial.

> Conocer el PIN no identifica a la persona. Decilo cuando estés solo, o escribilo. Lo crítico (correos, nivel 3 y cerraduras) sigue pidiendo confirmación en la pantalla.

## 4. Arrancar, consultar el estado y detener

```powershell
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py               # agente + API + voz; abre la interfaz
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --minimized   # igual, sin abrir el navegador
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --status      # estado, causa concreta y pasos por servicio
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --stop        # cierre limpio de la instancia en marcha
```

- **Arrancar dos veces no duplica nada:** la segunda vez avisa «SKY ya está en ejecución» y abre la interfaz.
- **Cerrar el navegador o el HUD no detiene a SKY.**
- Si un servicio se cae, el supervisor lo reinicia con espera progresiva (2, 4, 8, 16 y 32 s; como máximo 5 por hora y después cada 30 min).
- El supervisor nunca cierra programas ajenos ni otras instancias de SKY que no haya iniciado él.

Desde el menú `SKY_INICIAR.bat`: **0** = SKY completo · **7** = diagnóstico · **8** = inicio con Windows · **P** = PIN · **S** = detener.

## 5. Inicio automático con tu sesión de Windows

```powershell
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --install-startup
```

- Crea `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SKY_IA_Autonomo.bat`, que lanza SKY con `pythonw.exe`, sin ventana de consola.
- Corre en tu sesión, no como servicio de Windows, para tener micrófono, audio y apps de escritorio.
- Para que siga encendida enchufada: `powercfg /change standby-timeout-ac 0`. El instalador con `-Siempre` lo hace por vos.

## 6. Registros y diagnóstico

```powershell
Get-ChildItem .\local_data\logs\                         # supervisor.log, api.log, agent.log, voice.log…
Get-Content .\local_data\logs\supervisor.log -Tail 40
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --status | Out-File estado.json -Encoding utf8
```

- Cada archivo rota a los 2 MB y se guardan 3 copias.
- No incluyen el token del agente, las rutas con tus consultas ni lo que dijiste. Para ver las frases reconocidas al depurar, agregá `SKY_VOZ_DEPURAR=1` en `.env`; el PIN nunca se registra.

## 7. Módulos bajo demanda

Pedilo por voz o texto: «SKY, estado de los módulos», «activá el reconocimiento local», «activá el modelo local» o «qué le falta a WhatsApp». También podés abrir la ventana «Módulos» del HUD.

Ningún modelo pesado se carga al arrancar. Cada uno dice exactamente qué le falta: un paquete, un modelo o una variable de `.env`.

## 8. Volver atrás (reversión)

```powershell
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --stop
git checkout main                                # o la rama/commit que usabas antes (p. ej. e910f99)
git stash list                                   # si guardaste cambios en el paso 1:  git stash pop
```

- Tus datos no cambian de formato: memoria, agenda, KPIs y permisos funcionan igual en la versión anterior.
- Si querés quitar el inicio automático: `.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --uninstall-startup`.
- Archivos nuevos que podés borrar con seguridad si volvés atrás:
  - `%USERPROFILE%\.neuralt\sentinel_sesion.json`: estado de la sesión.
  - `%USERPROFILE%\.neuralt\sky_supervisor.json` y `sky_supervisor.lock`: estado del supervisor.
  - `.\local_data\logs\`: registros.
- El PIN (`sentinel.json`) ya existía en v12.5 y sigue siendo compatible.
