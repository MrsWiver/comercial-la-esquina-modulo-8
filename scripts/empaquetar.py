"""Empaqueta código, ejemplos autorizados y una SQLite recién creada, sin estado personal."""
import argparse
import json
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path
from src.db import ROOT, construir, conectar
from src.migraciones import migrar

ARCHIVOS=('README.md','AGENTS.md','pyproject.toml','uv.lock','.gitignore','.env.example')
CARPETAS=('src','templates','static','scripts','tests','soportes','prompts','docs','docente')
OMITIR={'__pycache__','.pytest_cache','.venv','.DS_Store','Icon\r'}

def empaquetar(destino):
    destino=Path(destino)
    destino.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='la-esquina-entrega-') as temporal:
        stage=Path(temporal)/'proyecto-inicial'
        stage.mkdir()
        for name in ARCHIVOS:
            shutil.copyfile(ROOT/name,stage/name)
        autorizados=json.loads((ROOT/'soportes/manifest.json').read_text())
        if len(autorizados)!=12:
            raise ValueError('La entrega requiere exactamente los 12 ejemplos autorizados.')
        nombres={x['archivo'] for x in autorizados}
        for x in autorizados:
            if hashlib.sha256((ROOT/'soportes'/x['archivo']).read_bytes()).hexdigest()!=x['sha256']:
                raise ValueError('Un soporte autorizado cambió. No se generó la entrega.')
        for name in (*CARPETAS,'datos/semilla'):
            for source in (ROOT/name).rglob('*'):
                relative=source.relative_to(ROOT)
                if any(part in OMITIR or part.startswith('.env') for part in relative.parts):
                    continue
                if source.is_file():
                    if name=='soportes' and source.name not in nombres|{'manifest.json','LEEME.txt'}:
                        continue
                    if name!='soportes' and source.suffix not in {'.py','.md','.txt','.json','.html','.css','.js'}:
                        continue
                    target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(source,target)
        (stage/'datos').mkdir(exist_ok=True)
        shutil.copyfile(ROOT/'datos/esquema.sql',stage/'datos/esquema.sql')
        (stage/'backend').mkdir()
        shutil.copyfile(ROOT/'backend/.env.example',stage/'backend/.env.example')
        construir(stage/'datos/practica/negocio.sqlite3')
        with conectar(stage/'datos/practica/negocio.sqlite3') as db:
            migrar(db)
        (stage/'datos/practica/.gitkeep').touch()
        with zipfile.ZipFile(destino,'w',compression=zipfile.ZIP_DEFLATED) as package:
            for source in sorted(stage.rglob('*')):
                if source.is_file() and source.name not in OMITIR:
                    package.write(source,source.relative_to(stage.parent))
    return destino

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--destino',type=Path,default=ROOT.parent/'proyecto-inicial-modulo-8.zip')
    print(empaquetar(parser.parse_args().destino))
