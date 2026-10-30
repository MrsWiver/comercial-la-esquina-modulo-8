from src.db import ROOT, construir

if __name__ == '__main__':
    destino=ROOT/'datos/practica/negocio.sqlite3'
    if destino.exists():
        print('La base ya existe; se conservaron tus datos. Para empezar de nuevo: uv run python -m scripts.reiniciar')
    else:
        construir(destino)
        print('Lista: datos/practica/negocio.sqlite3')
