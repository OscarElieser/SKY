"""Arranque manual de SKY Live: monitor local; detener con Ctrl+C."""
import argparse, time
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent/'.env')
from neural_core.sky_live import ejecutar_ciclo


def main():
    p=argparse.ArgumentParser(description='SKY Live: estado de BAQUEANO sin editar la web')
    p.add_argument('--intervalo',type=int,default=1800,help='Intervalo en segundos (mínimo 300)')
    args=p.parse_args()
    if not 300<=args.intervalo<=86400:p.error('Intervalo entre 300 y 86400 segundos')
    print('SKY Live activo en esta computadora. Ctrl+C para detener.')
    try:
        while True:
            result=ejecutar_ciclo()
            print('BAQUEANO:',result,flush=True)
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print('\nSKY Live detenido por el propietario.')


if __name__=='__main__':main()
