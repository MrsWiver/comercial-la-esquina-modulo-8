"""Sesiones persistentes para el bot de la home; las escrituras comerciales siguen autorizadas."""
import json
import time
from . import agente, ejercicios as e


def consultar(db, ident):
    row = db.execute('SELECT * FROM sesiones_asistente WHERE id=?',(ident,)).fetchone()
    e.exigir(row is not None, 'No encontré esta conversación.',404)
    e.exigir(not row['cancelada'], 'Esta operación fue cancelada. Adjunta un soporte para empezar de nuevo.',409)
    ext = e.consultar_extraccion(db,row['extraccion_id'])
    p=e.consultar_propuesta(db,row['propuesta_id']) if row['propuesta_id'] else None
    contenido=p['contenido'] if p else {}
    operacion=contenido.get('operacion',contenido)
    productos={}
    for linea in operacion.get('lineas',[]):
        producto=db.execute('SELECT nombre FROM productos WHERE codigo=?',(linea.get('producto_codigo'),)).fetchone()
        if producto:productos[linea['producto_codigo']]=producto[0]
    return {'id':row['id'],'extraccion':ext,'mensajes':json.loads(row['mensajes']), 'productos':productos,
            'propuesta':p,
            'ocupado':bool(row['ocupado'] and row['iniciado_en'] and time.time()-row['iniciado_en']<120)}


def iniciar(db, ext):
    row=db.execute('SELECT id FROM sesiones_asistente WHERE extraccion_id=?',(ext['id'],)).fetchone()
    if row:
        anterior=db.execute('SELECT cancelada FROM sesiones_asistente WHERE id=?',(row['id'],)).fetchone()
        if not anterior['cancelada']:return consultar(db,row['id'])
        db.execute('DELETE FROM sesiones_asistente WHERE id=?',(row['id'],))
    ident=e.nuevo('CHAT')
    db.execute('INSERT OR IGNORE INTO sesiones_asistente(id,extraccion_id) VALUES(?,?)',(ident,ext['id']))
    ident=db.execute('SELECT id FROM sesiones_asistente WHERE extraccion_id=?',(ext['id'],)).fetchone()[0]
    return consultar(db,ident)


def conversar(db,ident,texto):
    e.exigir(isinstance(texto,str) and 1<=len(texto.strip())<=3000, 'Escribe un mensaje de hasta 3000 caracteres.')
    db.execute('BEGIN IMMEDIATE')
    session=consultar(db,ident)
    e.exigir(not session['ocupado'], 'Estoy terminando tu consulta anterior. Espera un momento.',409)
    db.execute('UPDATE sesiones_asistente SET ocupado=1,iniciado_en=? WHERE id=?',(time.time(),ident))
    db.commit()
    contexto={'sesion_id':ident,'extraccion_id':session['extraccion']['id'],
              'propuesta_id':session['propuesta']['id'] if session['propuesta'] else None,'mensajes':session['mensajes']}
    try:
        respuesta=agente.responder(texto,db,contexto=contexto)
        mensajes=(session['mensajes']+[{'rol':'usuario','texto':texto},{'rol':'asistente','texto':respuesta}])[-100:]
        db.execute('BEGIN IMMEDIATE')
        activa(db,ident)
        db.execute('UPDATE sesiones_asistente SET mensajes=? WHERE id=?',(e.serializar(mensajes),ident))
        db.commit()
    finally:
        db.rollback()
        db.execute('UPDATE sesiones_asistente SET ocupado=0,iniciado_en=NULL WHERE id=?',(ident,))
        db.commit()
    return consultar(db,ident)


def activa(db, ident):
    row=db.execute('SELECT cancelada FROM sesiones_asistente WHERE id=?',(ident,)).fetchone()
    e.exigir(row is not None and not row['cancelada'], 'Esta operación fue cancelada.',409)


def solicitud(db, ident, archivo_id):
    if not ident:return
    e.exigir(isinstance(ident,str) and 1<=len(ident)<=80, 'Solicitud inválida.')
    db.execute('INSERT OR IGNORE INTO solicitudes_asistente(id,archivo_id) VALUES(?,?)',(ident,archivo_id))
    row=db.execute('SELECT * FROM solicitudes_asistente WHERE id=?',(ident,)).fetchone()
    e.exigir(not row['cancelada'], 'Esta operación fue cancelada.',409)
    e.exigir(row['archivo_id'] in (None,archivo_id), 'La solicitud pertenece a otro soporte.',409)
    db.execute('UPDATE solicitudes_asistente SET archivo_id=? WHERE id=?',(archivo_id,ident))
    db.commit()


def cancelar(db, datos):
    ident,solicitud_id=datos.get('sesion_id'),datos.get('solicitud_id')
    e.exigir(bool(ident or solicitud_id), 'Falta la operación que quieres cancelar.')
    e.exigir(all(x is None or isinstance(x,str) and 1<=len(x)<=80 for x in (ident,solicitud_id)), 'Operación inválida.')
    db.execute('BEGIN IMMEDIATE')
    if solicitud_id:
        db.execute('INSERT OR IGNORE INTO solicitudes_asistente(id,cancelada) VALUES(?,1)',(solicitud_id,))
        request=db.execute('SELECT * FROM solicitudes_asistente WHERE id=?',(solicitud_id,)).fetchone()
        ident=ident or request['sesion_id']
        db.execute('UPDATE solicitudes_asistente SET cancelada=1 WHERE id=?',(solicitud_id,))
    guardado=None
    if ident:
        row=db.execute('SELECT * FROM sesiones_asistente WHERE id=?',(ident,)).fetchone()
        if row:
            if row['propuesta_id']:
                p=e.consultar_propuesta(db,row['propuesta_id'])
                if p['estado']=='ejecutada':
                    guardado=p['resultado']
                elif not p['cancelada']:
                    db.execute('UPDATE propuestas SET cancelada=1,version=version+1 WHERE id=?',(p['id'],))
                    e.evento(db,p['id'],'propuesta_cancelada',{'version_anterior':p['version']})
            db.execute("UPDATE sesiones_asistente SET cancelada=1,mensajes='[]',ocupado=0,iniciado_en=NULL WHERE id=?",(ident,))
            db.execute('UPDATE solicitudes_asistente SET cancelada=1 WHERE sesion_id=?',(ident,))
            e.evento(db,ident,'conversacion_cancelada',{'resultado_guardado':bool(guardado)})
    return {'cancelada':True,'resultado_guardado':bool(guardado),'resultado':guardado}
