"""Servidor local para la base estudiantil. Inicio: uv run python -m src.app."""
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import tempfile
import warnings
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, jsonify, render_template, request, send_file
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

from . import ejercicios
from .chat import responder
from .db import ROOT, buscar_ventas, conectar, construir, consultar_venta

MAX_BYTES = 8 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 24_000_000


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def crear_app(data_dir=None):
    app = Flask(__name__, template_folder=str(ROOT/'templates'), static_folder=str(ROOT/'static'))
    app.config.update(MAX_CONTENT_LENGTH=MAX_BYTES+64*1024, TRUSTED_HOSTS=['127.0.0.1','localhost','[::1]'])
    carpeta = Path(data_dir) if data_dir else ROOT/'datos/practica'
    carpeta.mkdir(parents=True,exist_ok=True)
    base=carpeta/'negocio.sqlite3'
    if not base.exists():
        try:
            construir(base)
        except FileExistsError:
            pass
    uploads=carpeta/'archivos'
    uploads.mkdir(exist_ok=True)
    # Recuperación tras caída entre escritura de archivo y commit SQLite.
    # El proceso solo ejecuta esto al iniciar; usar una sola instancia local.
    with conectar(base) as db:
        conocidos={r[0] for r in db.execute('SELECT nombre_guardado FROM archivos_ingresados')}
    for archivo in uploads.iterdir():
        if archivo.name.endswith('.part') or (re.fullmatch(r'[a-f0-9]{64}\.(png|jpg)',archivo.name) and archivo.name not in conocidos):
            archivo.unlink()
    token=secrets.token_urlsafe(32)
    app.config['DB_PATH']=base
    app.config['UPLOAD_DIR']=uploads

    @app.before_request
    def proteger_escrituras():
        if request.method not in ('GET','HEAD','OPTIONS'):
            if not secrets.compare_digest(request.headers.get('X-Practica-Token',''),token):
                abort(403,description='Recarga la aplicación antes de continuar.')
            origen=request.headers.get('Origin')
            if origen and origen != request.host_url.rstrip('/'):
                abort(403,description='La solicitud debe venir de la aplicación local.')

    @app.after_request
    def cabeceras(respuesta):
        respuesta.headers['X-Content-Type-Options']='nosniff'
        respuesta.headers['Referrer-Policy']='no-referrer'
        respuesta.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' blob:; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        respuesta.headers['Cache-Control']='no-store'
        return respuesta

    @app.errorhandler(HTTPException)
    def error_http(e):
        mensaje='El archivo supera el límite de 8 MB.' if e.code==413 else e.description
        return jsonify(error=mensaje),e.code

    @app.errorhandler(sqlite3.Error)
    @app.errorhandler(OSError)
    def error_almacenamiento(e):
        return jsonify(error='No se pudo leer o guardar en el almacenamiento local. Revisa permisos y espacio; consulta los archivos antes de reintentar.'),503

    def cuerpo():
        valor=request.get_json(silent=True)
        if not isinstance(valor,dict):
            abort(400,description='Se esperaba un objeto JSON.')
        return valor

    def entero(valor,nombre,maximo=1_000_000_000):
        if not re.fullmatch(r'\d{1,10}',str(valor)) or int(valor)>maximo:
            abort(400,description=f'{nombre} debe ser un entero positivo dentro del rango permitido.')
        return int(valor)

    @app.get('/')
    def inicio():
        return render_template('index.html',csrf_token=token)

    @app.get('/api/resumen')
    def resumen():
        with conectar(base) as db:
            return jsonify(productos=db.execute('SELECT COUNT(*) FROM productos').fetchone()[0],
                           ventas=db.execute('SELECT COUNT(*) FROM ventas').fetchone()[0],
                           archivos=db.execute('SELECT COUNT(*) FROM archivos_ingresados').fetchone()[0],
                           modo='practica_sin_ia',version='0.1.0')

    @app.get('/api/ventas')
    def ventas():
        importe=request.args.get('importe')
        importe=entero(importe,'El importe') if importe is not None and importe!='' else None
        fecha=request.args.get('fecha','')
        if fecha:
            try:
                date.fromisoformat(fecha)
            except ValueError:
                abort(400,description='La fecha debe ser una fecha válida YYYY-MM-DD.')
        with conectar(base) as db:
            return jsonify(buscar_ventas(db,request.args.get('q','')[:150],importe,fecha))

    @app.get('/api/ventas/<venta_id>')
    def venta(venta_id):
        with conectar(base) as db:
            v=consultar_venta(db,venta_id)
            if not v:
                abort(404,description='No existe esa venta.')
            return jsonify(v)

    @app.get('/api/productos')
    def productos():
        q=request.args.get('q','')[:150]
        pagina=entero(request.args.get('pagina','1'),'La página',10000)
        if pagina<1:
            abort(400,description='La página empieza en 1.')
        with conectar(base) as db:
            term=f'%{q}%'
            total=db.execute('SELECT COUNT(*) FROM productos WHERE codigo LIKE ? OR nombre LIKE ?',(term,term)).fetchone()[0]
            filas=db.execute('SELECT codigo,nombre,categoria,unidad,precio_venta FROM productos WHERE codigo LIKE ? OR nombre LIKE ? ORDER BY codigo LIMIT 30 OFFSET ?',
                             (term,term,(pagina-1)*30)).fetchall()
            return jsonify(total=total,pagina=pagina,resultados=[dict(r) for r in filas])

    @app.get('/api/casos')
    def casos():
        return jsonify([{'nombre':p.name,'url':f'/soportes/{p.name}'} for p in sorted((ROOT/'soportes').glob('*.png'))])

    @app.get('/soportes/<nombre>')
    def soporte(nombre):
        if nombre not in {p.name for p in (ROOT/'soportes').glob('*.png')}:
            abort(404,description='No existe ese ejemplo.')
        return send_file(ROOT/'soportes'/nombre,mimetype='image/png')

    @app.get('/api/archivos')
    def archivos():
        with conectar(base) as db:
            return jsonify([dict(r) for r in db.execute('SELECT * FROM archivos_ingresados ORDER BY cargado_en DESC,id DESC')])

    @app.get('/archivos/<archivo_id>')
    def ver_archivo(archivo_id):
        with conectar(base) as db:
            fila=db.execute('SELECT * FROM archivos_ingresados WHERE id=?',(archivo_id,)).fetchone()
        if not fila:
            abort(404,description='No existe ese archivo.')
        path=uploads/fila['nombre_guardado']
        if not path.exists():
            abort(409,description='Falta el original en disco. Recupera el archivo desde tu respaldo; no se puede mostrar su evidencia.')
        return send_file(path,mimetype=fila['mime'],download_name=fila['nombre_original'])

    @app.post('/api/archivos')
    def cargar():
        adjunto=request.files.get('archivo')
        if not adjunto:
            abort(400,description='Selecciona un archivo PNG o JPEG.')
        extension=Path(adjunto.filename or '').suffix.lower()
        if extension not in ('.png','.jpg','.jpeg'):
            abort(400,description='Solo se admiten PNG y JPEG. PDF queda para una ampliación.')
        contenido=adjunto.read(MAX_BYTES+1)
        if len(contenido)>MAX_BYTES:
            abort(413)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(contenido)) as img:
                    formato=img.format
                    if formato not in ('PNG','JPEG') or img.width*img.height>24_000_000:
                        raise ValueError()
                    img.verify()
                with Image.open(io.BytesIO(contenido)) as img:
                    img.load()
        except (UnidentifiedImageError,OSError,ValueError,SyntaxError,Image.DecompressionBombError,Image.DecompressionBombWarning):
            abort(400,description='La imagen está dañada, no es PNG/JPEG válido o supera 24 millones de píxeles.')
        if (formato=='PNG') != (extension=='.png'):
            abort(400,description='La extensión no coincide con el contenido de la imagen.')
        digest=hashlib.sha256(contenido).hexdigest()
        nombre=digest+('.png' if formato=='PNG' else '.jpg')
        with conectar(base) as db:
            # Serializa la comprobación de duplicados y el guardado para doble clic.
            db.execute('BEGIN IMMEDIATE')
            existente=db.execute('SELECT * FROM archivos_ingresados WHERE sha256=?',(digest,)).fetchone()
            if existente:
                if not (uploads/nombre).exists():
                    abort(409,description='El registro existe pero falta el original. Recupera el respaldo antes de continuar.')
                return jsonify(archivo=dict(existente),duplicado=True),200
            fd,tmp=tempfile.mkstemp(dir=uploads,suffix='.part')
            destino=uploads/nombre
            try:
                with os.fdopen(fd,'wb') as f:
                    f.write(contenido);f.flush();os.fsync(f.fileno())
                os.replace(tmp,destino)
                archivo={'id':'ARC-'+uuid4().hex[:12],'sha256':digest,
                         'nombre_original':(secure_filename(adjunto.filename) or 'soporte'+extension)[:150],
                         'nombre_guardado':nombre,'mime':'image/png' if formato=='PNG' else 'image/jpeg',
                         'bytes':len(contenido),'cargado_en':ahora(),'estado':'pendiente_reconocimiento'}
                db.execute('INSERT INTO archivos_ingresados VALUES(:id,:sha256,:nombre_original,:nombre_guardado,:mime,:bytes,:cargado_en,:estado)',archivo)
                db.commit()
            except Exception:
                db.rollback()
                destino.unlink(missing_ok=True)
                raise
            finally:
                Path(tmp).unlink(missing_ok=True)
        return jsonify(archivo=archivo,duplicado=False),201

    @app.get('/api/chat')
    def historial():
        with conectar(base) as db:
            return jsonify([dict(r) for r in db.execute('SELECT * FROM (SELECT * FROM mensajes_chat ORDER BY id DESC LIMIT 100) ORDER BY id')])

    @app.post('/api/chat')
    def chat():
        texto=cuerpo().get('texto')
        if not isinstance(texto,str) or not 1<=len(texto.strip())<=1000:
            abort(400,description='Escribe entre 1 y 1000 caracteres.')
        with conectar(base) as db:
            respuesta=responder(texto,db)
            db.executemany('INSERT INTO mensajes_chat(rol,texto,creado_en) VALUES(?,?,?)',
                           [('usuario',texto,ahora()),('asistente',respuesta,ahora())])
        return jsonify(respuesta=respuesta)

    # Contratos de extensión: siempre 501 hasta completar el ejercicio respectivo.
    @app.post('/api/extraer/<archivo_id>')
    def extraer(archivo_id):
        with conectar(base) as db:
            archivo=db.execute('SELECT * FROM archivos_ingresados WHERE id=?',(archivo_id,)).fetchone()
            if not archivo:
                abort(404,description='Carga primero un archivo.')
            return pendiente(lambda:ejercicios.extraer_soporte(dict(archivo),db))

    def pendiente(accion):
        try:
            return jsonify(accion())
        except NotImplementedError as e:
            return jsonify(error=str(e),estado='pendiente_taller'),501

    @app.post('/api/comprobantes')
    def registrar():
        datos=cuerpo()
        with conectar(base) as db:
            return pendiente(lambda:ejercicios.registrar_comprobante(datos,db))

    @app.post('/api/propuestas')
    def preparar():
        datos=cuerpo()
        with conectar(base) as db:
            return pendiente(lambda:ejercicios.preparar_operacion(datos,db))

    @app.post('/api/propuestas/ejecutar')
    def ejecutar():
        datos=cuerpo()
        with conectar(base) as db:
            return pendiente(lambda:ejercicios.registrar_operacion_aprobada(datos,db))

    return app


if __name__ == '__main__':
    crear_app().run(host='127.0.0.1',port=8008,debug=False)
