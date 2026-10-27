# SKY — reutilizar dependencias instaladas y preservar el entorno (26/10/2026)

## Diagnóstico del equipo Windows del usuario

El usuario ya comprobó en su SKY de `D:\Desktop\SKY`:
- `.venv\Scripts\python.exe` EXISTE.
- `pip 25.0.1` dentro de `.venv`, con Python 3.12.
- `python -m pip check` ejecutado **dentro de .venv**: `No broken requirements found.`

El `KeyboardInterrupt` mostrado con `python -m pip ...` provino de
`D:\Python312\Lib\site-packages\pip`, el Python **global**, no el de SKY.
No demuestra corrupción del entorno virtual. No reinstalar Python ni borrar
el entorno por esa interrupción.

> `pip check` valida dependencias declaradas **entre paquetes instalados**;
> no demuestra por sí solo que absolutamente todos los paquetes de
> `requirements.txt` estén presentes.

## Verificación local sin cambiar archivos ni usar internet

En PowerShell dentro de `D:\Desktop\SKY`:

```powershell
& .\.venv\Scripts\python.exe .\scripts\sky_dependencias.py --requirements .\requirements.txt
& .\.venv\Scripts\python.exe -m pip check
```

También podés ejecutar `.\INSTALAR_SKY_WINDOWS.bat -SoloVerificarDependencias`,
que reutiliza `.venv` y retorna 0 cuando la lista está satisfecha, 1 cuando
faltan paquetes y 2 para requisitos no verificables.

## Modos del instalador

- `-SoloVerificarDependencias`: revisión de solo lectura con metadatos locales;
  NO instala, actualiza pip, inicia servicios, descarga modelos ni crea `.venv`.
- `-SoloDependencias`: reutiliza `.venv`, instala únicamente cuando hay
  requisitos ausentes/incompatibles y finaliza sin pasar por Ollama, PIN o
  ajustes 24/7. Si elegís `-SinVoz`, omite librerías opcionales de voz.
- `-SinVoz`: no instala las librerías opcionales
  `faster-whisper vosk sounddevice pyttsx3 psutil pywin32` ni sus modelos
  específicos de voz. `requirements.txt` aún contiene componentes como gTTS
  y torch: el perfil ligero **no elimina ni evita automáticamente todas las
  dependencias pesadas existentes**. Se necesita una lista de requisitos
  esenciales validada antes de prometer una instalación verdaderamente mínima.
- `-SinOllama`: no instala Ollama ni descarga modelos del cerebro.
- `-ActualizarPip`: único caso que ejecuta una actualización automática
  de pip dentro de `.venv`. Por defecto se conserva la versión instalada.

### Ejemplo sin instalar IA local ni voz

```powershell
Set-Location "D:\Desktop\SKY"
.\INSTALAR_SKY_WINDOWS.bat -SoloDependencias -SinOllama -SinVoz
```

**Nunca** aplicar `git reset --hard`, eliminar `.venv` o borrar `.env`
para solucionar un `KeyboardInterrupt`. Tampoco instalar con `python -m pip`
sin verificar primero cuál Python se está ejecutando.

## Validación CI y sus límites

- Pruebas aisladas del verificador de metadatos en Linux y Windows.
- Validación estática de sintaxis del instalador PowerShell sin ejecutarlo.
- No son pruebas del entorno físico de trabajo o casa.
- La ejecución real del instalador, reinicio, energía, Ollama y RAM debe
  verificarse presencialmente en los equipos autorizados.
