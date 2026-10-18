"""Diagnóstico local y verificable de SKY: no realiza llamadas a servicios externos.

Las comprobaciones de bases de datos son de solo lectura y las capacidades
opcionales se muestran por separado, sin afirmar que una API esté conectada.
"""
from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
import os
import sqlite3
from datetime import datetime, timezone

DEPENDENCIES = {
    'api': ('fastapi',),
    'metaverso': ('trimesh', 'numpy'),
    'oficina': ('docx', 'pptx', 'xlsxwriter', 'reportlab'),
    'vision_2d': ('PIL',),
    'creative_studio': ('PIL','fastapi','multipart'),
}


def _database_info(path: Path) -> dict:
    if not path.exists():
        return {'state': 'not_initialized', 'message': 'Se creará con el primer uso'}
    if not path.is_file():
        return {'state': 'error', 'message': 'Ruta no es archivo SQLite'}
    try:
        # No se crea ni modifica la base de datos durante el diagnóstico.
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2) as conn:
            status = conn.execute('PRAGMA quick_check(1)').fetchone()[0]
        return {'state': 'ready' if status == 'ok' else 'error',
                'message': 'Integridad OK' if status == 'ok' else 'Integridad fallida'}
    except (sqlite3.Error, OSError, ValueError):
        return {'state': 'error', 'message': 'No se puede abrir o verificar la base de datos'}


def integration_status() -> dict:
    from metaverse.store import path_db as worlds_path
    from metaverse.community_store import db_path as community_path
    from .sky_workbench import _db_path as work_path
    from .sky_projects import db_path as projects_path
    from .sky_workflows import db_path as workflow_path
    from .sky_intelligent import db_path as intelligent_path

    libraries = {}
    for name, modules in DEPENDENCIES.items():
        missing = [mod for mod in modules if find_spec(mod) is None]
        libraries[name] = {'state': 'ready' if not missing else 'missing_dependency',
                           'missing': missing}

    from .sky_creative import db_path as creative_db
    databases = {
        'metaverso': _database_info(Path(worlds_path())),
        'comunidad': _database_info(Path(community_path())),
        'proyectos_y_memoria': _database_info(Path(work_path())),
        'proyectos_compartidos_entre_modulos': _database_info(Path(projects_path())),
        'automatizaciones_persistentes': _database_info(Path(workflow_path())),
        'workspace_inteligente': _database_info(Path(intelligent_path())),
        'biblioteca_multimedia': _database_info(Path(creative_db())),
    }
    critical = libraries['api']['state'] == 'ready' and all(
        info['state'] != 'error' for info in databases.values())
    extras = [name for name, info in libraries.items()
              if name != 'api' and info['state'] != 'ready']
    return {
        'service': 'SKY Integration Center',
        'version': '9.2.0',  # Versión del contrato de diagnóstico heredado
        'platform_version': '9.7.0',
        'creative_render_ffmpeg': bool(__import__('shutil').which('ffmpeg') and __import__('shutil').which('ffprobe')),
        'state': 'ready' if critical and not extras else 'degraded' if critical else 'attention_required',
        'core_operational': critical,
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'libraries': libraries,
        'databases': databases,
        'external_providers': 'not_checked',
        'hardware': 'not_checked',
        'scope': 'Comprobación local de dependencias y SQLite; no certifica despliegue público ni conexiones externas',
    }
