"""Revisión, propuestas versionadas y efectos comerciales autorizados en servidor."""
import hashlib
import json
import math
from datetime import date, datetime, time, timezone
from uuid import uuid4
from pathlib import Path
from jsonschema import Draft202012Validator
from .db import ROOT, consultar_venta
from . import ia

OCR_MODEL = 'gpt-5.6-luna'
SCHEMA = json.loads((ROOT / 'prompts/extraccion-v1.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


class ErrorNegocio(Exception):
    def __init__(self, mensaje, status=400):
        super().__init__(mensaje)
        self.status = status


def exigir(condicion, mensaje, status=400):
    if not condicion:
        raise ErrorNegocio(mensaje, status)


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def nuevo(prefijo):
    return prefijo + '-' + uuid4().hex[:16]


def serializar(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def evento(db, entidad, tipo, detalle=None):
    db.execute('INSERT INTO eventos(entidad_id,tipo,detalle,creado_en) VALUES(?,?,?,?)',
               (entidad, tipo, serializar(detalle or {}), ahora()))


def fila(db, tabla, ident):
    # Nombres internos, nunca procedentes de la solicitud o del modelo.
    exigir(tabla in ('extracciones', 'propuestas', 'comprobantes', 'operaciones'), 'Entidad inválida.')
    row = db.execute(f'SELECT * FROM {tabla} WHERE id=?', (ident,)).fetchone()
    exigir(row is not None, 'No existe el registro solicitado.', 404)
    return dict(row)


def validar_extraccion(datos):
    try:
        serializar(datos)
    except (ValueError, TypeError):
        raise ErrorNegocio('La extracción contiene valores no finitos o no serializables.') from None
    errores = list(VALIDATOR.iter_errors(datos))
    exigir(not errores, 'Extracción fuera del contrato: ' + ('.'.join(map(str, errores[0].path)) if errores else ''))
    if datos['document_date']:
        try:
            date.fromisoformat(datos['document_date'])
        except ValueError:
            raise ErrorNegocio('La fecha extraída no existe.') from None
    if datos['document_time']:
        time.fromisoformat(datos['document_time'])
        exigir(datos['time_precision'] is not None, 'La hora necesita una precisión.')
        exigir(datos['time_precision'] != 'minute' or datos['document_time'].endswith(':00'), 'La precisión de minuto requiere segundos 00.')
    else:
        exigir(datos['time_precision'] is None, 'Una precisión de hora requiere una hora.')
    exigir(datos['amount_basis'] != 'missing' or datos['total_amount'] is None, 'Un total ausente debe permanecer en null.')
    exigir(datos['amount_basis'] == 'missing' or datos['total_amount'] is not None, 'Un monto observado o financiado requiere un total.')
    if datos['document_type'] in ('addi_credit', 'sistecredito_credit'):
        exigir(datos['amount_basis'] in ('financed_value', 'missing'), 'Un crédito es financiación, no dinero recibido.')
    for k in ('total_amount', 'inferred_amount', 'stated_cash_amount'):
        exigir(datos[k] is None or math.isfinite(datos[k]), 'Importe no finito.')
    return datos


def extraer_soporte(archivo, db, origen='api_real'):
    existente = db.execute('SELECT * FROM extracciones WHERE archivo_id=?', (archivo['id'],)).fetchone()
    if existente:
        return consultar_extraccion(db, existente['id'])
    # En pruebas y otras carpetas, la ruta sale del registro de configuración SQLite.
    base = db.execute('PRAGMA database_list').fetchone()[2]
    path = Path(base).parent / 'archivos' / archivo['nombre_guardado']
    exigir(path.is_file(), 'Falta el original de este soporte.', 409)
    try:
        datos = validar_extraccion(ia.reconocer(path, archivo['mime']))
    except (ia.ErrorIA, ErrorNegocio) as exc:
        evento(db, archivo['id'], 'extraccion_fallida', {'tipo': type(exc).__name__})
        db.commit()
        raise
    db.execute('BEGIN IMMEDIATE')
    existente = db.execute('SELECT id FROM extracciones WHERE archivo_id=?', (archivo['id'],)).fetchone()
    if existente:
        return consultar_extraccion(db, existente['id'])
    ident = nuevo('EXT')
    db.execute('INSERT INTO extracciones VALUES(?,?,?,?,?,?,?)',
        (ident, archivo['id'], serializar(datos), OCR_MODEL, ahora(), origen,
         hashlib.sha256((ROOT / 'prompts/extractor-v1.txt').read_bytes()).hexdigest()))
    evento(db, ident, 'extraccion_guardada', {'modelo': OCR_MODEL})
    return consultar_extraccion(db, ident)


def consultar_extraccion(db, ident):
    r = fila(db, 'extracciones', ident)
    r['original'] = json.loads(r['original'])
    r['comprobante_id'] = next((x[0] for x in db.execute('SELECT id FROM comprobantes WHERE extraccion_id=?', (ident,))), None)
    return r


def consultar_propuesta(db, ident):
    r = fila(db, 'propuestas', ident)
    r['contenido'] = json.loads(r['contenido'])
    r['resultado'] = json.loads(r['resultado']) if r['resultado'] else None
    return r


def entero(value, nombre):
    exigir(type(value) is int and 0 < value <= 1_000_000_000, nombre + ' debe ser un entero positivo en pesos, sin redondeo.')
    return value


def validar_contenido(db, tipo, datos, completo=True):
    exigir(isinstance(datos, dict), 'Se requiere contenido de propuesta.')
    if tipo == 'registrar_comprobante':
        ext = consultar_extraccion(db, datos.get('extraccion_id'))
        exigir(not ext['comprobante_id'], 'La extracción ya tiene un comprobante registrado.', 409)
        revision = validar_extraccion(datos.get('revision'))
        # Una fracción debe conservarse; el diseño entero bloquea el registro comercial.
        for fuente in (ext['original'], revision):
            for campo in ('total_amount', 'inferred_amount', 'stated_cash_amount'):
                n = fuente[campo]
                exigir(n is None or float(n).is_integer(), 'El soporte contiene fracciones de peso. Extracción conservada; requiere revisar el diseño monetario.', 409)
        exigir(isinstance(datos.get('motivo'), str) and 3 <= len(datos['motivo'].strip()) <= 1000, 'Escribe el motivo o constancia de la revisión.')
        return {'extraccion_id': ext['id'], 'revision': revision, 'motivo': datos['motivo'].strip()}
    exigir(tipo in ('asociar', 'crear_venta', 'adjuntar_soporte'), 'Tipo de propuesta no permitido.')
    if not completo:
        return datos
    c = fila(db, 'comprobantes', datos.get('comprobante_id'))
    r = json.loads(c['revision'])
    if tipo == 'adjuntar_soporte':
        op = fila(db, 'operaciones', datos.get('operacion_id'))
        exigir(not db.execute('SELECT 1 FROM soportes_operacion WHERE comprobante_id=?', (c['id'],)).fetchone(), 'El comprobante ya está vinculado.', 409)
        exigir(datos.get('confirmacion_mismo_documento') is True, 'Confirma que ambos soportes describen la misma operación.')
        exigir(r['total_amount'] == op['monto'], 'Los importes difieren; revisa la operación antes de adjuntar.')
        naturaleza='financiacion' if r['amount_basis']=='financed_value' else 'gasto' if r['document_type']=='expense' else 'cobro'
        exigir(r['document_type'] is not None and naturaleza==op['naturaleza'] and r['currency_observed'] in (None,op['moneda']), 'La naturaleza o moneda no coincide con la operación existente.')
        return {'comprobante_id': c['id'], 'operacion_id': op['id'], 'confirmacion_mismo_documento': True}
    exigir(not db.execute('SELECT 1 FROM soportes_operacion WHERE comprobante_id=?', (c['id'],)).fetchone(), 'Este comprobante ya describe una operación. Consulta su vínculo.', 409)
    exigir(r['document_type'] not in (None, 'expense'), 'Un documento sin clasificación o de gasto no permite registrar un ingreso.')
    importe_observado = r['total_amount']
    exigir(type(importe_observado) in (int,float) and math.isfinite(importe_observado) and float(importe_observado).is_integer(), 'Monto ausente o con fracciones; no se redondea.')
    monto = entero(int(importe_observado), 'El monto revisado')
    exigir(r['amount_basis'] != 'missing', 'No hay un monto observado para aplicar.')
    exigir(datos.get('moneda_confirmada') == 'COP', 'Confirma explícitamente la moneda COP.')
    exigir(r['currency_observed'] in (None, 'COP'), 'La moneda observada requiere revisión; solo se admite COP.')
    exigir(datos.get('confirmacion_operacion_unica') is True, 'Compara referencias y soportes existentes; confirma que no duplicas la misma operación.')
    # Referencias iguales no crean automáticamente otro movimiento de dinero.
    refs = {k: v for k, v in r['references'].items() if v and k != 'invoice'}
    for op in db.execute('SELECT referencias FROM operaciones'):
        existentes = json.loads(op[0])
        exigir(not any(existentes.get(k) == v for k, v in refs.items()), 'Existe una operación con la misma referencia. Revisa y adjunta el soporte a esa operación.', 409)
    base = {'comprobante_id': c['id'], 'moneda_confirmada': 'COP', 'confirmacion_operacion_unica': True,
            'monto': monto, 'naturaleza': 'financiacion' if r['amount_basis'] == 'financed_value' else 'cobro'}
    if tipo == 'asociar':
        venta = consultar_venta(db, datos.get('venta_id'))
        exigir(venta is not None, 'Selecciona una venta existente.', 404)
        base['venta_id'] = venta['id']
        total = venta['total']
        aplicado = db.execute('SELECT COALESCE(SUM(importe),0) FROM vinculos WHERE venta_id=?', (venta['id'],)).fetchone()[0]
    else:
        exigir(datos.get('confirmacion_venta_faltante') is True, 'Confirma con el comerciante que falta registrar la venta.')
        try:
            fecha = date.fromisoformat(datos.get('fecha_comercial', ''))
        except (TypeError, ValueError):
            raise ErrorNegocio('Indica una fecha comercial válida.') from None
        lineas = datos.get('lineas')
        exigir(isinstance(lineas, list) and 0 < len(lineas) <= 100, 'Completa las líneas de la venta.')
        normalizadas, codigos, total = [], set(), 0
        for linea in lineas:
            exigir(isinstance(linea, dict), 'Línea inválida.')
            codigo = linea.get('producto_codigo')
            exigir(isinstance(codigo, str) and codigo not in codigos, 'Selecciona códigos únicos del catálogo.')
            p = db.execute('SELECT precio_venta FROM productos WHERE codigo=?', (codigo,)).fetchone()
            exigir(p is not None, 'Producto inexistente en catálogo.')
            cantidad = entero(linea.get('cantidad'), 'La cantidad')
            exigir(linea.get('precio_unitario') == p[0] and type(linea.get('precio_unitario')) is int, 'Confirma el precio vigente del catálogo.')
            normalizadas.append({'producto_codigo': codigo, 'cantidad': cantidad, 'precio_unitario': p[0]})
            total += cantidad * p[0]
            codigos.add(codigo)
        exigir(total <= 1_000_000_000, 'Total comercial fuera del rango permitido.')
        for k in ('cliente', 'factura_externa'):
            exigir(datos.get(k) is None or isinstance(datos[k], str) and 0 < len(datos[k]) <= 150, 'Cliente y factura deben ser texto o null.')
        base.update(fecha_comercial=fecha.isoformat(), cliente=datos.get('cliente'), factura_externa=datos.get('factura_externa'),
                    lineas=normalizadas, total=total, confirmacion_venta_faltante=True)
        aplicado = 0
    importe = entero(datos.get('importe_aplicado'), 'El importe aplicado')
    exigir(importe <= monto and importe <= total - aplicado, 'El importe supera el monto del soporte o el saldo comercial de la venta.')
    base['importe_aplicado'] = importe
    return base


def preparar_operacion(datos, db):
    exigir(isinstance(datos, dict), 'Propuesta inválida.')
    try:
        exigir(len(serializar(datos)) <= 64000, 'La propuesta supera el límite de tamaño.')
    except (ValueError, TypeError):
        raise ErrorNegocio('La propuesta contiene valores no válidos.') from None
    tipo = datos.get('tipo')
    borrador = datos.get('borrador') is True
    exigir(not borrador or tipo in ('asociar', 'crear_venta'), 'Solo una operación comercial puede quedar incompleta.')
    contenido = validar_contenido(db, tipo, datos.get('contenido'), not borrador)
    db.execute('BEGIN IMMEDIATE')
    ident = datos.get('id')
    if ident:
        anterior = consultar_propuesta(db, ident)
        exigir(anterior['estado'] != 'ejecutada', 'Una propuesta ejecutada es inmutable.', 409)
        exigir(type(datos.get('version')) is int and anterior['version'] == datos['version'], 'La versión cambió. Recarga la propuesta.', 409)
        version = anterior['version'] + 1
        db.execute('UPDATE propuestas SET tipo=?,contenido=?,version=?,estado=?,resultado=NULL WHERE id=?',
                   (tipo, serializar(contenido), version, 'borrador' if borrador else 'pendiente', ident))
    else:
        ident, version = nuevo('PROP'), 1
        db.execute('INSERT INTO propuestas VALUES(?,?,?,?,?,?,NULL)',
                   (ident, version, tipo, serializar(contenido), 'borrador' if borrador else 'pendiente', ahora()))
    evento(db, ident, 'propuesta_preparada', {'version': version, 'tipo': tipo})
    return consultar_propuesta(db, ident)


def registrar_comprobante(datos, db):
    return preparar_operacion({'tipo': 'registrar_comprobante', 'contenido': datos}, db)


def aprobar(db, ident, datos):
    db.execute('BEGIN IMMEDIATE')
    p = consultar_propuesta(db, ident)
    exigir(datos.get('version') == p['version'] and type(datos.get('version')) is int, 'La versión cambió. Revisa de nuevo.', 409)
    exigir(p['estado'] in ('pendiente', 'aprobada'), 'La propuesta no admite aprobación.', 409)
    exigir(datos.get('confirmacion') == 'REVISADO', 'Revisa el contenido y confirma mediante la interfaz.')
    validar_contenido(db, p['tipo'], p['contenido'])
    digest = hashlib.sha256(serializar(p['contenido']).encode()).hexdigest()
    db.execute('INSERT OR IGNORE INTO aprobaciones VALUES(?,?,?,?,?)', (nuevo('APR'), ident, p['version'], digest, ahora()))
    db.execute("UPDATE propuestas SET estado='aprobada' WHERE id=?", (ident,))
    evento(db, ident, 'aprobacion_humana', {'version': p['version']})
    return consultar_propuesta(db, ident)


def registrar_operacion_aprobada(datos, db):
    db.execute('BEGIN IMMEDIATE')
    p = consultar_propuesta(db, datos.get('id'))
    exigir(type(datos.get('version')) is int and datos['version'] == p['version'], 'Versión desactualizada.', 409)
    if p['estado'] == 'ejecutada':
        return p['resultado']
    aprobacion = db.execute('SELECT * FROM aprobaciones WHERE propuesta_id=? AND version=?', (p['id'], p['version'])).fetchone()
    exigir(p['estado'] == 'aprobada' and aprobacion is not None and
           aprobacion['contenido_sha256'] == hashlib.sha256(serializar(p['contenido']).encode()).hexdigest(),
           'Falta la aprobación humana de esta versión emitida por el servidor.', 409)
    d = validar_contenido(db, p['tipo'], p['contenido'])
    if p['tipo'] == 'registrar_comprobante':
        ident = nuevo('CMP')
        db.execute('INSERT INTO comprobantes(id,extraccion_id,revision,propuesta_id,creado_en) VALUES(?,?,?,?,?)',
                   (ident, d['extraccion_id'], serializar(d['revision']), p['id'], ahora()))
        original = consultar_extraccion(db, d['extraccion_id'])['original']
        for campo, valor in d['revision'].items():
            if valor != original[campo]:
                db.execute('INSERT INTO correcciones(comprobante_id,campo,original,corregido,origen,motivo) VALUES(?,?,?,?,?,?)',
                           (ident, campo, serializar(original[campo]), serializar(valor), 'revision_humana', d['motivo']))
        resultado = {'comprobante_id': ident}
    elif p['tipo'] == 'adjuntar_soporte':
        db.execute('INSERT INTO soportes_operacion VALUES(?,?)', (d['comprobante_id'], d['operacion_id']))
        resultado = {'operacion_id': d['operacion_id'], 'comprobante_id': d['comprobante_id']}
    else:
        c = fila(db, 'comprobantes', d['comprobante_id'])
        r = json.loads(c['revision'])
        operacion_id = nuevo('OP')
        db.execute('INSERT INTO operaciones(id,naturaleza,monto,moneda,referencias) VALUES(?,?,?,?,?)',
                   (operacion_id, d['naturaleza'], d['monto'], 'COP', serializar(r['references'])))
        db.execute('INSERT INTO soportes_operacion VALUES(?,?)', (c['id'], operacion_id))
        venta_id = d.get('venta_id')
        if p['tipo'] == 'crear_venta':
            venta_id = nuevo('V')
            db.execute('INSERT INTO ventas(id,fecha_comercial,cliente,factura_externa,origen) VALUES(?,?,?,?,?)',
                       (venta_id, d['fecha_comercial'], d['cliente'], d['factura_externa'], 'registro_humano'))
            db.executemany('INSERT INTO venta_lineas(venta_id,producto_codigo,cantidad,precio_unitario) VALUES(?,?,?,?)',
                           [(venta_id, l['producto_codigo'], l['cantidad'], l['precio_unitario']) for l in d['lineas']])
        vinculo_id = nuevo('VIN')
        db.execute('INSERT INTO vinculos VALUES(?,?,?,?,?)', (vinculo_id, operacion_id, venta_id, d['importe_aplicado'], p['id']))
        resultado = {'venta_id': venta_id, 'operacion_id': operacion_id, 'vinculo_id': vinculo_id,
                     'importe_aplicado': d['importe_aplicado'], 'estado_financiero': 'no_verificado'}
    db.execute('INSERT INTO ejecuciones VALUES(?,?,?,?)', (p['id'] + ':' + str(p['version']), p['id'], serializar(resultado), ahora()))
    db.execute("UPDATE propuestas SET estado='ejecutada',resultado=? WHERE id=?", (serializar(resultado), p['id']))
    evento(db, p['id'], 'ejecucion', resultado)
    return resultado


def consultar_comprobante(db, ident):
    r = fila(db, 'comprobantes', ident)
    r['revision'] = json.loads(r['revision'])
    r['extraccion'] = consultar_extraccion(db, r['extraccion_id'])
    r['correcciones'] = [dict(x) for x in db.execute('SELECT * FROM correcciones WHERE comprobante_id=?', (ident,))]
    r['operaciones'] = [dict(x) for x in db.execute('SELECT o.*,v.id AS vinculo_id,v.venta_id,v.importe FROM soportes_operacion s JOIN operaciones o ON o.id=s.operacion_id LEFT JOIN vinculos v ON v.operacion_id=o.id WHERE s.comprobante_id=?', (ident,))]
    return r
