"""SKY Smart Memory v12.0.

Gestor integral de memoria estructurada con control de privacidad:
- Memoria de Sesión (efímera / temporal)
- Memoria de Proyecto (contexto técnico y repositorio)
- Preferencias de Usuario (estilo, idioma, nivel académico)
- Conocimientos Documentales (RAG / fragmentos indexados)
- Operaciones completas CRUD: consultar, actualizar, eliminar y exportar (JSON).
- Estricta separación entre datos privados de usuario y contexto público.
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class MemoryEntry:
    id: str
    categoria: str # "sesion", "proyecto", "preferencia", "documental"
    clave: str
    valor: Any
    es_privado: bool = True
    usuario_id: str = "default_user"
    timestamp: float = 0.0
    modificado: float = 0.0


class SmartMemoryManager:
    """Administrador de memoria en capas con persistencia segura y control de privacidad."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("local_data/sky_smart_memory.json")
        self._entries: Dict[str, MemoryEntry] = {}
        self._cargar()

    def _cargar(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for item in data:
                    entry = MemoryEntry(**item)
                    self._entries[entry.id] = entry
            except Exception:
                self._entries = {}

    def _guardar(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(entry) for entry in self._entries.values()]
        self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def guardar_memoria(
        self,
        categoria: str,
        clave: str,
        valor: Any,
        usuario_id: str = "default_user",
        es_privado: bool = True
    ) -> MemoryEntry:
        """Almacena o actualiza una memoria controlada por el usuario."""
        now = time.time()
        mem_id = f"{usuario_id}:{categoria}:{clave}"
        
        if mem_id in self._entries:
            entry = self._entries[mem_id]
            entry.valor = valor
            entry.modificado = now
            entry.es_privado = es_privado
        else:
            entry = MemoryEntry(
                id=mem_id,
                categoria=categoria,
                clave=clave,
                valor=valor,
                es_privado=es_privado,
                usuario_id=usuario_id,
                timestamp=now,
                modificado=now
            )
            self._entries[mem_id] = entry

        self._guardar()
        return entry

    def consultar_memorias(
        self,
        usuario_id: str = "default_user",
        categoria: Optional[str] = None,
        incluir_privadas: bool = True
    ) -> List[MemoryEntry]:
        """Recupera memorias filtradas por usuario y categoría respetando permisos de privacidad."""
        res = []
        for entry in self._entries.values():
            if entry.usuario_id != usuario_id:
                continue
            if categoria and entry.categoria != categoria:
                continue
            if not incluir_privadas and entry.es_privado:
                continue
            res.append(entry)
        return res

    def eliminar_memoria(self, mem_id: str, usuario_id: str = "default_user") -> bool:
        """Elimina una memoria específica por orden del usuario."""
        if mem_id in self._entries and self._entries[mem_id].usuario_id == usuario_id:
            del self._entries[mem_id]
            self._guardar()
            return True
        return False

    def exportar_memorias_json(self, usuario_id: str = "default_user") -> str:
        """Exporta en formato JSON todas las memorias del usuario para portabilidad."""
        mems = self.consultar_memorias(usuario_id=usuario_id, incluir_privadas=True)
        return json.dumps([asdict(m) for m in mems], indent=2, ensure_ascii=False)

    def vaciar_memorias_usuario(self, usuario_id: str = "default_user") -> int:
        """Borrado seguro de todas las memorias asociadas a un usuario."""
        ids_to_del = [m.id for m in self._entries.values() if m.usuario_id == usuario_id]
        for mid in ids_to_del:
            del self._entries[mid]
        if ids_to_del:
            self._guardar()
        return len(ids_to_del)


# Instancia singleton global para el ciclo de vida de la aplicación
_default_memory_manager: Optional[SmartMemoryManager] = None

def get_smart_memory_manager() -> SmartMemoryManager:
    global _default_memory_manager
    if _default_memory_manager is None:
        _default_memory_manager = SmartMemoryManager()
    return _default_memory_manager
