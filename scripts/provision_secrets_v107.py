"""Local Docker secret provisioning only; never publishes credentials."""
from __future__ import annotations
import argparse
import base64
import os
import secrets
from pathlib import Path


def provision(directory: Path) -> dict:
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError('Directorio de secretos simbólico no admitido')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if any(directory.iterdir()):
        raise FileExistsError('Directorio no vacío: no se sobrescribirán secretos')
    password = secrets.token_hex(32)
    mfa = base64.b32encode(secrets.token_bytes(32)).decode('ascii').rstrip('=')
    contents = {
        'sky_api_key.txt': secrets.token_urlsafe(48),
        'sky_mfa_seed.txt': mfa,
        'sky_redis_password.txt': password,
        'redis.conf': ('bind 0.0.0.0\nprotected-mode yes\nport 6379\n'
                       'save ""\nappendonly no\nmaxmemory 64mb\n'
                       'maxmemory-policy allkeys-lru\nrequirepass '+password+'\n'),
    }
    for name, content in contents.items():
        path = directory/name
        fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content+'\n' if not content.endswith('\n') else content)
    return {'created': sorted(contents), 'directory': str(directory),
            'owner_mfa_enrollment_requires_local_secret_read': True,
            'no_secrets_in_report': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default='deploy/secrets')
    args = parser.parse_args()
    print(provision(Path(args.directory)))

if __name__ == '__main__':
    main()
