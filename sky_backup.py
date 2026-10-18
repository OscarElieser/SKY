"""Create consistent, owner-only SQLite backups using SQLite online backup API.

Run locally or from cron/systemd after securing the backup directory.
"""
from __future__ import annotations
import sqlite3,os
from pathlib import Path
from datetime import datetime,timezone
from metaverse.store import path_db as worlds_db
from metaverse.community_store import db_path as community_db
from neural_core.sky_workbench import _db_path as workbench_db
from neural_core.sky_projects import db_path as projects_db
from neural_core.sky_workflows import db_path as workflows_db
from neural_core.sky_intelligent import db_path as intelligent_db
from neural_core.sky_telemetry import ROOT as TELEMETRY_ROOT
import shutil,json,hashlib

def backup(destination:Path|str|None=None,include_extended:bool=False):
    root=Path(__file__).resolve().parent
    dest=Path(destination) if destination else root/'backups'
    dest.mkdir(parents=True,exist_ok=True)
    os.chmod(dest,0o700)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    files=[]
    sources=[('mundos',worlds_db()),('comunidad',community_db())]
    if include_extended:
        from neural_core.sky_creative import db_path as creative_db
        sources += [('workbench',workbench_db()),
                    ('creative_studio',creative_db()),
                    ('proyectos',projects_db()),
                    ('flujos',workflows_db()),
                    ('workspace_inteligente',intelligent_db()),
                    ('telemetria',Path(os.getenv('SKY_TELEMETRY_DB') or TELEMETRY_ROOT/'local_data'/'sky_telemetry.sqlite3')),
                    ('evolucion',Path(os.getenv('SKY_EVOLUTION_DB') or root/'data'/'sky_evolution.sqlite3'))]
    for label,src in sources:
        if not src.exists():continue
        target=dest/f'SKY_{label}_{stamp}.sqlite3'
        with sqlite3.connect(f'file:{src}?mode=ro',uri=True) as source,sqlite3.connect(target) as copy:
            source.backup(copy)
        os.chmod(target,0o600)
        with sqlite3.connect(target) as copy:
            if copy.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                target.unlink(missing_ok=True)
                raise RuntimeError(f'Integridad no válida: {label}')
        files.append(str(target))
    # Respalda, cuando existan, los documentos guardados por el orquestador.
    outputs=Path(os.getenv('SKY_BACKUP_OUTPUTS') or root/'local_data'/'sky_outputs')
    if include_extended and outputs.is_dir():
        private=dest/f'SKY_archivos_{stamp}';private.mkdir(mode=0o700)
        hashes={}
        for src in outputs.iterdir():
            if not src.is_file() or src.is_symlink():continue
            if src.stat().st_size>100_000_000:continue
            target=private/src.name
            shutil.copy2(src,target);os.chmod(target,0o600)
            hashes[src.name]=hashlib.sha256(target.read_bytes()).hexdigest()
        (private/'SHA256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
        os.chmod(private/'SHA256.json',0o600)
        files.append(str(private))
    if include_extended:
        from neural_core.sky_creative import store_dir
        media=store_dir()/'media'
        if media.is_dir():
            dest_media=dest/f'SKY_media_{stamp}'
            dest_media.mkdir(mode=0o700)
            hashes={}
            for src in media.iterdir():
                if not src.is_file() or src.is_symlink() or src.stat().st_size>80_000_000:continue
                target=dest_media/src.name
                shutil.copy2(src,target);os.chmod(target,0o600)
                hashes[src.name]=hashlib.sha256(target.read_bytes()).hexdigest()
            (dest_media/'SHA256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
            files.append(str(dest_media))
    return files

if __name__=='__main__':
    for path in backup(include_extended=True):print('Respaldo verificado:',path)
