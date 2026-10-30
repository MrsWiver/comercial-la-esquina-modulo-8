"""Reinicia solo el estado local, conservando DB y archivos en un respaldo."""
import shutil
from datetime import datetime, timezone
from src.db import ROOT, construir

if __name__ == '__main__':
    print('Detén la aplicación antes de reiniciar. Se respaldarán la base, imágenes y chat.')
    if input('Escribe REINICIAR para continuar: ').strip() != 'REINICIAR':
        raise SystemExit('Sin cambios.')
    practica=ROOT/'datos/practica'
    respaldo=ROOT/'datos'/'respaldos'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    respaldo.parent.mkdir(exist_ok=True)
    shutil.move(str(practica),str(respaldo))
    try:
        construir(practica/'negocio.sqlite3')
    except Exception:
        shutil.rmtree(practica,ignore_errors=True)
        shutil.move(str(respaldo),str(practica))
        raise
    print(f'Base inicial restaurada. Respaldo completo: {respaldo}')
