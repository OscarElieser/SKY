"""Local release scanner: high-signal secret patterns and excluded artifacts.

Does not replace SAST, DAST, dependency audit, penetration testing or MFA audits.
Usage: python scripts/security_audit_v103.py [path]
"""
from __future__ import annotations
import json,re,sys,zipfile,subprocess
from pathlib import Path

SECRET_PATTERNS={
    'github_token':re.compile(rb'gh[pousr]_[A-Za-z0-9_]{30,}'),
    'openai_token':re.compile(rb'sk-[A-Za-z0-9_-]{30,}'),
    'google_api_key':re.compile(rb'AIza[0-9A-Za-z_-]{30,}'),
    'aws_access_key':re.compile(rb'AKIA[A-Z0-9]{16}'),
    'private_key_header':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
}
FORBIDDEN_NAMES={'.env','id_rsa','id_ed25519','credentials.json','service-account.json'}
FORBIDDEN_SUFFIXES={'.pem','.p12','.pfx','.sqlite','.sqlite3','.db'}
MAX_READ=1_000_000


def dangerous_name(name:str)->bool:
    path=Path(name)
    return (path.name.lower() in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES
        or 'local_data' in path.parts or '__pycache__' in path.parts or '.git' in path.parts)


def scan_release(path:Path)->dict:
    flagged=[];examined=0;bytes_scanned=0
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path) as z:
            entries=((info.filename,info.file_size,lambda info=info:z.read(info)) for info in z.infolist() if not info.is_dir())
            for name,size,read in entries:
                examined+=1
                if dangerous_name(name):flagged.append({'path':name,'reason':'private_file_name'})
                if size>MAX_READ:continue
                data=read();bytes_scanned+=len(data)
                # Do not leak candidate secret material into output.
                for label,pat in SECRET_PATTERNS.items():
                    if pat.search(data):flagged.append({'path':name,'reason':label})
    else:
        git_files=None
        if (path/'.git').is_dir():
            scanned=subprocess.run(['git','ls-files','-z'],cwd=path,capture_output=True,timeout=10,check=True)
            git_files={name.decode('utf-8') for name in scanned.stdout.split(b'\0') if name}
        for f in path.rglob('*'):
            if not f.is_file():continue
            rel=f.relative_to(path).as_posix()
            if git_files is not None and rel not in git_files:continue
            if any(s in ('.git','__pycache__','.pytest_cache','.venv','venv','local_data') for s in f.relative_to(path).parts) and git_files is None:continue
            rel=f.relative_to(path).as_posix()
            examined+=1
            if dangerous_name(rel):flagged.append({'path':rel,'reason':'private_file_name'})
            if f.stat().st_size>MAX_READ:continue
            data=f.read_bytes();bytes_scanned+=len(data)
            for label,pat in SECRET_PATTERNS.items():
                if pat.search(data):flagged.append({'path':rel,'reason':label})
    return {'scanned_files':examined,'scanned_bytes':bytes_scanned,'issues':flagged,
            'limitations':'No sustituye auditoría de dependencias ni prueba de penetración'}

if __name__=='__main__':
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
    result=scan_release(root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(1 if result['issues'] else 0)
