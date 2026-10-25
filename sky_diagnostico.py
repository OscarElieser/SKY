"""Autodiagnóstico de SKY: qué funciona, qué falta y cómo arreglarlo."""
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))
from neural_core.sky_diagnostico import main

if __name__ == '__main__':
    main()
