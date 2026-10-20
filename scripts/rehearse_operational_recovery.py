"""Create and verify a real encrypted SKY backup, then restore it temporarily."""
from __future__ import annotations
import json,os,sys,tempfile,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from neural_core import sky_recovery_full as recovery

def main():
    if not os.getenv('SKY_BACKUP_PASSPHRASE'):
        raise SystemExit('SKY_BACKUP_PASSPHRASE no está configurada')
    backup_dir=ROOT/'backups_hardened'
    backup_dir.mkdir(exist_ok=True)
    target=backup_dir/f"sky-{time.strftime('%Y%m%d-%H%M%S')}.skybackup"
    created=recovery.create(target)
    verified=recovery.verify(target)
    with tempfile.TemporaryDirectory(prefix='sky-recovery-rehearsal-') as temporary:
        destination=Path(temporary)/'restored'
        restored=recovery.restore_to_empty(target,destination)
        db_files=list((destination/'db').glob('*.sqlite3'))
        media_files=[p for p in (destination/'media').rglob('*') if p.is_file()] if (destination/'media').exists() else []
        if len(db_files)!=created['sqlite'] or len(media_files)!=created['media']:
            raise RuntimeError('La restauración no contiene todos los archivos esperados')
    report={'backup':str(target),'created':created,'verified':verified,
            'restored_files':restored['files'],'temporary_restore_removed':True}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
