"""SKY local preflight: python sky_preflight.py [--json]. No network calls."""
from __future__ import annotations
import argparse, json
from neural_core.sky_integrations import integration_status


def main():
    parser=argparse.ArgumentParser(description='Comprobar módulos y bases de datos locales de SKY IA')
    parser.add_argument('--json', action='store_true', help='Mostrar informe estructurado')
    args=parser.parse_args()
    report=integration_status()
    if args.json:
        print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print('SKY IA · Diagnóstico de integración v'+report['version'])
        print('Estado:',report['state'])
        for name, item in report['libraries'].items():
            print('  Módulo', name+':',item['state'], ' '.join(item['missing']))
        for name, item in report['databases'].items():
            print('  Datos',name+':',item['state'])
        print('No se verificaron proveedores IA externos ni dispositivos físicos.')
    return 0 if report['core_operational'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
