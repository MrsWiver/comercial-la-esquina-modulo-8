"""SQLite local. Semilla independiente del proyecto anterior; importes en COP enteros."""
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@contextmanager
def conectar(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    try:
        with db:
            yield db
    finally:
        db.close()


def construir(destino):
    """Solo crea bases nuevas. Para volver al inicio se conserva una copia completa."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        raise FileExistsError('La base ya existe. Usa scripts.reiniciar para conservar un respaldo.')
    fd, temporal = tempfile.mkstemp(dir=destino.parent, suffix='.sqlite3.tmp')
    os.close(fd)
    try:
        with conectar(temporal) as db:
            db.executescript((ROOT / 'datos/esquema.sql').read_text())
            catalogo = json.loads((ROOT / 'datos/semilla/catalogo.json').read_text())
            for tabla in ('proveedores','productos','inventario'):
                filas = catalogo[tabla]
                columnas = list(filas[0])
                sql = f'INSERT INTO {tabla} ({",".join(columnas)}) VALUES ({",".join("?" for _ in columnas)})'
                db.executemany(sql, [tuple(f[c] for c in columnas) for f in filas])
            ventas = json.loads((ROOT / 'datos/semilla/ventas.json').read_text())
            for v in ventas:
                db.execute('INSERT INTO ventas(id,fecha_comercial,cliente,factura_externa) VALUES(?,?,?,?)',
                           (v['id'],v['fecha_comercial'],v['cliente'],v['factura_externa']))
                db.executemany('INSERT INTO venta_lineas(venta_id,producto_codigo,cantidad,precio_unitario) VALUES(?,?,?,?)',
                    [(v['id'], l['producto_codigo'],l['cantidad'],l['precio_unitario']) for l in v['lineas']])
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
        # El enlace falla si otra instancia ganó la creación: nunca sobreescribe.
        os.link(temporal, destino)
    finally:
        Path(temporal).unlink(missing_ok=True)


def buscar_ventas(db, texto='', importe=None, fecha=None):
    filtros, valores = [], []
    if texto:
        filtros.append('(id LIKE ? OR COALESCE(cliente,\'\') LIKE ? OR COALESCE(factura_externa,\'\') LIKE ?)')
        valores += [f'%{texto}%']*3
    if importe is not None:
        filtros.append('total = ?')
        valores.append(importe)
    if fecha:
        filtros.append('fecha_comercial = ?')
        valores.append(fecha)
    where = ' WHERE ' + ' AND '.join(filtros) if filtros else ''
    return [dict(r) for r in db.execute('SELECT * FROM resumen_ventas'+where+' ORDER BY fecha_comercial DESC,id LIMIT 100', valores)]


def consultar_venta(db, venta_id):
    fila = db.execute('SELECT * FROM resumen_ventas WHERE id=?',(venta_id,)).fetchone()
    if not fila:
        return None
    venta = dict(fila)
    venta['lineas'] = [dict(r) for r in db.execute('''
        SELECT l.producto_codigo,p.nombre,l.cantidad,l.precio_unitario,
               l.cantidad*l.precio_unitario AS subtotal
        FROM venta_lineas l JOIN productos p ON p.codigo=l.producto_codigo
        WHERE l.venta_id=? ORDER BY l.id''',(venta_id,))]
    return venta
