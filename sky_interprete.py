"""SKY Intérprete — modo opcional para que SKY escriba y ejecute código en tu PC.

Usa Open Interpreter (https://github.com/OpenInterpreter/open-interpreter) con tu
modelo LOCAL de Ollama por defecto, así nada sale de tu equipo.

    pip install open-interpreter
    ollama pull llama3.1            # o el modelo que prefieras
    python sky_interprete.py         # o SKY_INICIAR.bat → opción I

SKY muestra cada bloque de código y espera tu "y" antes de ejecutarlo. Es lo que
permite automatizar cualquier cosa (organizar archivos, convertir documentos,
programar, administrar el sistema) sin que una frase mal entendida borre o
sobrescriba algo. Este modo es independiente de la voz y del HUD: lo abrís vos.
"""
from __future__ import annotations

import argparse
import os
import sys

INSTRUCCIONES_SKY = """
Te llamás SKY, el asistente personal de Oscar Elieser Chamorro Guzmán. Hablá en español.
Antes de cada bloque de código explicá en una frase qué va a hacer.
Si el código borra, mueve, sobrescribe, instala o desinstala algo, o cambia configuración del
sistema, decilo explícitamente ("Esto va a BORRAR…") y preferí opciones reversibles
(papelera en lugar de borrado, copia de seguridad antes de sobrescribir).
Nunca uses comandos para obtener contraseñas, tokens o datos de otras personas.
"""


def main(argv=None) -> None:
    modelo_local = 'ollama/' + os.getenv('OLLAMA_MODEL', 'llama3.1')
    p = argparse.ArgumentParser(description='SKY Intérprete: código en tu PC, con confirmación de cada paso.')
    p.add_argument('--modelo', default=os.getenv('SKY_INTERPRETER_MODEL', modelo_local),
                   help=f'Modelo LiteLLM (por defecto {modelo_local}, local con Ollama)')
    args = p.parse_args(argv)
    try:
        from interpreter import interpreter
    except ImportError:
        sys.exit('Falta Open Interpreter. Instalalo con:  pip install open-interpreter')
    local = args.modelo.startswith('ollama/')
    if not local and os.getenv('SKY_LOCAL_ONLY', '0') == '1':
        sys.exit('SKY_LOCAL_ONLY=1 está activo: usá un modelo ollama/… para no enviar datos fuera del equipo.')
    interpreter.llm.model = args.modelo
    if local:
        interpreter.offline = True
        interpreter.llm.api_base = os.getenv('OLLAMA_API_BASE', 'http://127.0.0.1:11434')
    interpreter.auto_run = False          # SIEMPRE muestra el código y pide confirmación
    interpreter.system_message += INSTRUCCIONES_SKY
    print('SKY Intérprete · modelo', args.modelo, '· local' if local else '· NUBE')
    print('Cada bloque de código se muestra antes de ejecutarse: respondé "y" para correrlo o "n" para saltarlo.')
    interpreter.chat()


if __name__ == '__main__':
    main()
