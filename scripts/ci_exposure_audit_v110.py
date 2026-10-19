"""Distinguish image EXPOSE from actual HOST-PUBLISHED ports in Docker Compose.

A container may expose port 8765 internally without binding that port to the
host. Only a strictly positive PublishedPort constitutes a host publication.
"""
from __future__ import annotations
import json
import sys


INTERNAL={'api','renderer','redis'}
REQUIRED=INTERNAL|{'proxy'}


def verify(items):
    if not isinstance(items,list) or any(not isinstance(x,dict) for x in items):
        raise ValueError('Salida Compose inválida')
    names={item.get('Service') for item in items}
    if not REQUIRED<=names:
        raise ValueError('Falta un servicio Docker')
    for item in items:
        if item.get('Service') not in INTERNAL:
            continue
        ports=item.get('Publishers') or []
        if not isinstance(ports,list):
            raise ValueError('Formato de puertos inválido')
        for port in ports:
            if not isinstance(port,dict):
                raise ValueError('Entrada de puerto inválida')
            value=port.get('PublishedPort')
            if value is None or value=='':
                continue
            try:
                published=int(value)
            except (TypeError,ValueError):
                raise ValueError('Puerto publicado inválido') from None
            if published<0 or published>65535:
                raise ValueError('Puerto publicado inválido')
            if published>0:
                raise ValueError(f'Puerto de host inesperado: {item["Service"]}')
    return {'services':sorted(names),'internal_host_ports':0,'verified':True}


def parse(text:str):
    if not text.strip():
        raise ValueError('Compose no devolvió servicios')
    if text.lstrip().startswith('['):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main():
    report=verify(parse(sys.stdin.read()))
    print(json.dumps(report))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
