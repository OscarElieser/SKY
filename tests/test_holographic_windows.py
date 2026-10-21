"""
Pruebas unitarias para el gestor de ventanas holográficas de SKY-IA.
Verifica:
- Apertura, cierre, minimización, restauración de ventanas.
- Reubicación y redimensionamiento de ventanas.
- Comando "dejá solo el núcleo" y "minimizá todo".
- Interpretación de comandos por voz para YouTube, chat, documentos, proyectos y módulos.
"""

import pytest
from neural_core.window_manager import HolographicWindowManager, gestor_ventanas


def test_window_manager_lifecycle():
    wm = HolographicWindowManager()

    # Inicialmente ninguna ventana está abierta
    assert len(wm.get_open_windows()) == 0

    # Abrir ventana multimedia
    w_media = wm.open_window('multimedia', title='Reproductor', position='top-right')
    assert w_media.is_open is True
    assert w_media.is_minimized is False
    assert len(wm.get_open_windows()) == 1

    # Minimizar ventana
    wm.minimize_window('multimedia')
    assert len(wm.get_open_windows()) == 0
    assert len(wm.get_dock_items()) == 1

    # Restaurar ventana
    wm.restore_window('multimedia')
    assert len(wm.get_open_windows()) == 1
    assert len(wm.get_dock_items()) == 0

    # Redimensionar
    wm.resize_window('multimedia', 'mini')
    assert wm.windows['multimedia'].size == 'mini'

    # Mover
    wm.move_window('multimedia', 'top-left')
    assert wm.windows['multimedia'].position == 'top-left'

    # Cerrar
    wm.close_window('multimedia')
    assert len(wm.get_open_windows()) == 0


def test_multiple_windows_and_leave_only_core():
    wm = HolographicWindowManager()

    # Abrir varias ventanas
    wm.open_window('multimedia', position='top-left')
    wm.open_window('chat', position='bottom-left')
    wm.open_window('documents', position='right')

    open_wins = wm.get_open_windows()
    assert len(open_wins) == 3

    # Minimizar todas
    wm.minimize_all()
    assert len(wm.get_open_windows()) == 0
    assert len(wm.get_dock_items()) == 3

    # Restaurar todas
    wm.restore_all()
    assert len(wm.get_open_windows()) == 3

    # "Dejá solo el núcleo"
    wm.leave_only_core()
    assert len(wm.get_open_windows()) == 0
    assert len(wm.get_dock_items()) == 0


def test_window_voice_commands():
    wm = HolographicWindowManager()

    # "dejá solo el núcleo"
    wm.open_window('chat')
    res = wm.parse_window_command("SKY, dejá solo el núcleo")
    assert res is not None
    assert res['subaction'] == 'leave_only_core'
    assert len(wm.get_open_windows()) == 0

    # "abrí el chat"
    res = wm.parse_window_command("SKY, abrí el chat")
    assert res is not None
    assert res['subaction'] == 'open_chat'
    assert wm.windows['chat'].is_open is True

    # "abrí mis documentos"
    res = wm.parse_window_command("SKY, abrí mis documentos")
    assert res is not None
    assert res['subaction'] == 'open_documents'
    assert wm.windows['documents'].is_open is True

    # "poné la música a la izquierda"
    wm.open_window('multimedia')
    res = wm.parse_window_command("SKY, poné la música a la izquierda")
    assert res is not None
    assert res['subaction'] == 'move_window'
    assert wm.windows['multimedia'].position == 'top-left'

    # "hacé pequeña esa ventana"
    wm.active_window_id = 'multimedia'
    res = wm.parse_window_command("SKY, hacé pequeña esa ventana")
    assert res is not None
    assert res['subaction'] == 'resize_window'
    assert wm.windows['multimedia'].size == 'mini'

    # "ampliá YouTube"
    res = wm.parse_window_command("SKY, ampliá YouTube")
    assert res is not None
    assert res['subaction'] == 'resize_window'
    assert wm.windows['multimedia'].size == 'ampliado'

    # "minimizá todo"
    res = wm.parse_window_command("SKY, minimizá todo")
    assert res is not None
    assert res['subaction'] == 'minimize_all'

    # "mostrá las ventanas"
    res = wm.parse_window_command("SKY, mostrá las ventanas")
    assert res is not None
    assert res['subaction'] == 'restore_all'

    # "cerrá el reproductor"
    res = wm.parse_window_command("SKY, cerrá el reproductor")
    assert res is not None
    assert res['subaction'] == 'close_multimedia'
    assert wm.windows['multimedia'].is_open is False
