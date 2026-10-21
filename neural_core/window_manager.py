"""
SKY-IA — Gestor de Ventanas Holográficas Inteligentes (Holographic Window Manager)
Control centralizado de ventanas inteligentes alrededor del Núcleo 3D.
Autoría conceptual: Oscar Elieser Chamorro Guzmán.
"""

import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class HolographicWindow:
    id: str
    title: str
    win_type: str  # 'multimedia', 'chat', 'documents', 'projects', 'modules', 'custom'
    is_open: bool = False
    is_minimized: bool = False
    is_maximized: bool = False
    position: str = 'top-right'  # 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'right', 'left'
    size: str = 'normal'  # 'mini', 'normal', 'ampliado', 'fullscreen'
    z_index: int = 10
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'win_type': self.win_type,
            'is_open': self.is_open,
            'is_minimized': self.is_minimized,
            'is_maximized': self.is_maximized,
            'position': self.position,
            'size': self.size,
            'z_index': self.z_index,
            'data': self.data,
        }


class HolographicWindowManager:
    """Administra las ventanas holográficas que orbitan alrededor del núcleo 3D de SKY-IA."""

    def __init__(self):
        self.windows: Dict[str, HolographicWindow] = {}
        self.active_window_id: Optional[str] = None
        self._next_z = 20
        self._init_default_windows()

    def _init_default_windows(self):
        # Ventana multimedia (reproductor YouTube / audio / video)
        self.windows['multimedia'] = HolographicWindow(
            id='multimedia',
            title='🎬 Reproductor Holográfico',
            win_type='multimedia',
            is_open=False,
            position='top-right',
            size='normal',
            data={'url': '', 'video_id': '', 'query': ''}
        )
        # Ventana de diálogo / chat con SKY-IA
        self.windows['chat'] = HolographicWindow(
            id='chat',
            title='💬 Conversación SKY-IA',
            win_type='chat',
            is_open=False,
            position='bottom-left',
            size='normal'
        )
        # Ventana de documentos y Office Studio
        self.windows['documents'] = HolographicWindow(
            id='documents',
            title='📁 Documentos & Office Studio',
            win_type='documents',
            is_open=False,
            position='right',
            size='normal',
            data={'current_doc': ''}
        )
        # Ventana de proyectos y tareas
        self.windows['projects'] = HolographicWindow(
            id='projects',
            title='✅ Proyectos & Tareas Activas',
            win_type='projects',
            is_open=False,
            position='bottom-right',
            size='normal'
        )
        # Ventana de catálogo de los 26 módulos
        self.windows['modules'] = HolographicWindow(
            id='modules',
            title='🧠 Ecosistema SKY-IA (26 Módulos)',
            win_type='modules',
            is_open=False,
            position='left',
            size='normal'
        )

    def open_window(self, win_id: str, win_type: Optional[str] = None, title: Optional[str] = None,
                    position: Optional[str] = None, size: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> HolographicWindow:
        if win_id not in self.windows:
            self.windows[win_id] = HolographicWindow(
                id=win_id,
                title=title or f"Ventana {win_id}",
                win_type=win_type or 'custom',
                position=position or 'top-right',
                size=size or 'normal',
                data=data or {}
            )
        win = self.windows[win_id]
        win.is_open = True
        win.is_minimized = False
        if position:
            win.position = position
        if size:
            win.size = size
        if data:
            win.data.update(data)
        if title:
            win.title = title
        self._next_z += 1
        win.z_index = self._next_z
        self.active_window_id = win_id
        return win

    def close_window(self, win_id: str) -> bool:
        if win_id in self.windows:
            self.windows[win_id].is_open = False
            self.windows[win_id].is_minimized = False
            if self.active_window_id == win_id:
                self.active_window_id = None
            return True
        return False

    def minimize_window(self, win_id: str) -> bool:
        if win_id in self.windows and self.windows[win_id].is_open:
            self.windows[win_id].is_minimized = True
            return True
        return False

    def maximize_window(self, win_id: str) -> bool:
        if win_id in self.windows:
            self.windows[win_id].is_open = True
            self.windows[win_id].is_minimized = False
            self.windows[win_id].is_maximized = True
            self.windows[win_id].size = 'ampliado'
            self._next_z += 1
            self.windows[win_id].z_index = self._next_z
            self.active_window_id = win_id
            return True
        return False

    def restore_window(self, win_id: str) -> bool:
        if win_id in self.windows:
            win = self.windows[win_id]
            win.is_open = True
            win.is_minimized = False
            win.is_maximized = False
            win.size = 'normal'
            self._next_z += 1
            win.z_index = self._next_z
            self.active_window_id = win_id
            return True
        return False

    def move_window(self, win_id: str, new_position: str) -> bool:
        if win_id in self.windows:
            valid_positions = {'top-left', 'top-right', 'bottom-left', 'bottom-right', 'left', 'right', 'center-right'}
            if new_position in valid_positions:
                self.windows[win_id].position = new_position
                return True
        return False

    def resize_window(self, win_id: str, new_size: str) -> bool:
        if win_id in self.windows:
            valid_sizes = {'mini', 'normal', 'ampliado', 'fullscreen'}
            if new_size in valid_sizes:
                self.windows[win_id].size = new_size
                if new_size == 'fullscreen':
                    self.windows[win_id].is_maximized = True
                return True
        return False

    def minimize_all(self):
        """Minimiza todas las ventanas abiertas al dock discreto."""
        for win in self.windows.values():
            if win.is_open:
                win.is_minimized = True

    def restore_all(self):
        """Restaura todas las ventanas abiertas y no minimizadas."""
        for win in self.windows.values():
            if win.is_open:
                win.is_minimized = False

    def leave_only_core(self):
        """Oculta las ventanas secundarias dejando únicamente el núcleo 3D visible, sin destruir datos."""
        for win in self.windows.values():
            win.is_open = False
            win.is_minimized = False
        self.active_window_id = None

    def get_open_windows(self) -> List[HolographicWindow]:
        return [w for w in self.windows.values() if w.is_open and not w.is_minimized]

    def get_dock_items(self) -> List[HolographicWindow]:
        return [w for w in self.windows.values() if w.is_open and w.is_minimized]

    def parse_window_command(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Interpreta comandos de voz o texto para gestión de ventanas inteligentes.
        """
        import unicodedata
        raw = text.lower().strip()
        raw = re.sub(r'^(?:sky|sky-ia|hey sky)[,;:\s]*', '', raw).strip()
        # Normalizar caracteres con tildes a forma base (ej: abrí -> abri, dejá -> deja)
        clean = ''.join(c for c in unicodedata.normalize('NFD', raw) if unicodedata.category(c) != 'Mn')

        # 1. Dejar solo el núcleo
        if re.search(r'\b(?:deja|deja\s+solo|deja\s+unicamente|solo\s+el|oculta\s+las\s+ventanas|limpia\s+la\s+pantalla)\b', clean):
            if 'nucleo' in clean or 'solo' in clean or 'oculta' in clean:
                self.leave_only_core()
                return {'action': 'holographic_window', 'subaction': 'leave_only_core',
                        'message': 'Ventanas ocultas. Mostrando únicamente el núcleo holográfico central.'}

        # 2. Minimizar todo
        if re.search(r'\b(?:minimiza|minimizar)\s+(?:todo|todas|todas\s+las\s+ventanas)\b', clean):
            self.minimize_all()
            return {'action': 'holographic_window', 'subaction': 'minimize_all',
                    'message': 'Todas las ventanas fueron minimizadas al dock holográfico.'}

        # 3. Mostrar las ventanas / restaurar todo
        if re.search(r'\b(?:muestra|mostrar|mostra|restaura|restaurar)\s+(?:las\s+)?ventanas\b', clean):
            self.restore_all()
            return {'action': 'holographic_window', 'subaction': 'restore_all',
                    'message': 'Restaurando ventanas holográficas activas.'}

        # 4. Cerrar reproductor
        if re.search(r'\b(?:cierra|cerrar|cerra|quita|quitar)\s+(?:el\s+)?(?:reproductor|video|musica|youtube)\b', clean):
            self.close_window('multimedia')
            return {'action': 'holographic_window', 'subaction': 'close_multimedia',
                    'message': 'Reproductor holográfico cerrado.'}

        # 5. Cerrar ventana activa o genérica
        m_close_win = re.search(r'\b(?:cierra|cerrar|cerra)\s+(?:la\s+)?ventana(?:\s+de\s+|\s+del\s+)?([a-z0-9_\-\. ]+)?\b', clean)
        if m_close_win:
            target = (m_close_win.group(1) or '').strip()
            if 'chat' in target:
                self.close_window('chat')
                return {'action': 'holographic_window', 'subaction': 'close_chat', 'message': 'Ventana de chat cerrada.'}
            elif 'document' in target or 'word' in target or 'office' in target:
                self.close_window('documents')
                return {'action': 'holographic_window', 'subaction': 'close_docs', 'message': 'Ventana de documentos cerrada.'}
            elif 'proyecto' in target or 'tarea' in target:
                self.close_window('projects')
                return {'action': 'holographic_window', 'subaction': 'close_projects', 'message': 'Ventana de proyectos cerrada.'}
            elif 'modulo' in target:
                self.close_window('modules')
                return {'action': 'holographic_window', 'subaction': 'close_modules', 'message': 'Ventana de módulos cerrada.'}
            elif self.active_window_id:
                wid = self.active_window_id
                self.close_window(wid)
                return {'action': 'holographic_window', 'subaction': f'close_{wid}', 'message': f'Ventana {wid} cerrada.'}

        # 6. Mover ventana a posición
        # "poné la música a la izquierda"
        if re.search(r'\b(?:pone|pon|mover?|traslada|trasladar)\s+(?:la\s+)?(?:musica|reproductor|video|youtube)\s+(?:a\s+la\s+|al\s+)?(izquierda|derecha|arriba|abajo)\b', clean):
            m_pos = re.search(r'(izquierda|derecha|arriba|abajo)', clean)
            direction = m_pos.group(1) if m_pos else 'izquierda'
            pos_map = {'izquierda': 'top-left', 'derecha': 'top-right', 'arriba': 'top-right', 'abajo': 'bottom-right'}
            self.move_window('multimedia', pos_map.get(direction, 'top-left'))
            return {'action': 'holographic_window', 'subaction': 'move_window', 'target': 'multimedia',
                    'message': f'Reproductor reubicado a la {direction}.'}

        # "mové los documentos a la derecha"
        if re.search(r'\b(?:pone|pon|mover?)\s+(?:los\s+)?(?:documentos|proyectos|herramientas|office)\s+(?:a\s+la\s+|al\s+)?(izquierda|derecha)\b', clean):
            m_pos = re.search(r'(izquierda|derecha)', clean)
            direction = m_pos.group(1) if m_pos else 'derecha'
            target_win = 'documents' if 'document' in clean or 'office' in clean else 'projects'
            self.move_window(target_win, 'right' if direction == 'derecha' else 'left')
            return {'action': 'holographic_window', 'subaction': 'move_window', 'target': target_win,
                    'message': f'Ventana de {target_win} ubicada a la {direction}.'}

        # 7. Redimensionar ventana
        # "hacé pequeña esa ventana" / "hacé chica esa ventana"
        if re.search(r'\b(?:hace|hacer|pon|pone|cambia|cambiar)\s+(?:pequena|pequeña|chica|mini)\s+(?:esa\s+)?ventana\b|\bventana\s+mini\b', clean):
            target = self.active_window_id or 'multimedia'
            self.resize_window(target, 'mini')
            return {'action': 'holographic_window', 'subaction': 'resize_window', 'target': target, 'size': 'mini',
                    'message': f'Ventana {target} reducida a formato mini.'}

        # "ampliá YouTube" / "ampliar reproductor"
        if re.search(r'\b(?:amplia|ampliar|agranda|agrandar)\s+(?:youtube|reproductor|video|esa\s+ventana)\b', clean):
            target = 'multimedia' if ('youtube' in clean or 'reproductor' in clean or 'video' in clean) else (self.active_window_id or 'multimedia')
            self.resize_window(target, 'ampliado')
            return {'action': 'holographic_window', 'subaction': 'resize_window', 'target': target, 'size': 'ampliado',
                    'message': f'Ventana {target} ampliada.'}

        # 8. Abrir herramientas en ventanas holográficas
        # "SKY, abrí el chat"
        if re.search(r'\b(?:abre|abrir|abri|mostrar?|ver)\s+(?:el\s+)?chat\b', clean):
            self.open_window('chat', win_type='chat', title='💬 Conversación SKY-IA', position='bottom-left')
            return {'action': 'holographic_window', 'subaction': 'open_chat',
                    'message': 'Ventana de chat flotante abierta.'}

        # "SKY, abrí mis documentos"
        if re.search(r'\b(?:abre|abrir|abri|mostrar?|ver)\s+(?:mis\s+)?documentos\b', clean):
            self.open_window('documents', win_type='documents', title='📁 Documentos & Office Studio', position='right')
            return {'action': 'holographic_window', 'subaction': 'open_documents',
                    'message': 'Ventana holográfica de documentos abierta.'}

        # "SKY, mostrá mis proyectos"
        if re.search(r'\b(?:abre|abrir|abri|mostrar?|mostra|ver)\s+(?:mis\s+)?proyectos\b', clean):
            self.open_window('projects', win_type='projects', title='✅ Proyectos & Tareas Activas', position='bottom-right')
            return {'action': 'holographic_window', 'subaction': 'open_projects',
                    'message': 'Ventana de proyectos y tareas abierta.'}

        # "SKY, mostrá mis módulos"
        if re.search(r'\b(?:abre|abrir|abri|mostrar?|mostra|ver)\s+(?:mis\s+)?(?:modulos|herramientas|aplicaciones)\b', clean):
            self.open_window('modules', win_type='modules', title='🧠 Ecosistema SKY-IA (26 Módulos)', position='left')
            return {'action': 'holographic_window', 'subaction': 'open_modules',
                    'message': 'Catálogo de módulos abierto en ventana holográfica.'}

        return None


# Instancia singleton del gestor de ventanas
gestor_ventanas = HolographicWindowManager()
