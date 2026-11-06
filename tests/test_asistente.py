"""Recorrido de home con respuestas simuladas y cero llamadas reales a OpenAI."""
import json
import pytest
from src import ejercicios as e,ia,agente
from src.app import crear_app
from src.db import conectar
from test_base import headers,upload
from test_flujo import lectura,post,datos_venta_054,aprobar_ejecutar

@pytest.fixture
def app(tmp_path,monkeypatch):
    app=crear_app(tmp_path/'practica');app.config.update(TESTING=True,OCR_ORIGEN='mock_prueba')
    monkeypatch.setattr(ia,'reconocer',lambda *a:lectura(148000))
    return app

@pytest.fixture
def client(app):return app.test_client()

def sesion(client):
    archivo=upload(client).json['archivo']
    r=post(client,'/api/asistente/iniciar/'+archivo['id'],{})
    assert r.status_code==200,r.json
    return r.json

def contenido(s):
    d=datos_venta_054(None)
    return {'registro':{'extraccion_id':s['extraccion']['id'],'revision':s['extraccion']['original'],
        'motivo':'Confirmación final del original y resumen de prueba'},'tipo_operacion':'crear_venta','operacion':d}

def propuesta(client,s):
    r=post(client,'/api/propuestas',{'tipo':'resolver_soporte','contenido':contenido(s)})
    assert r.status_code==200,r.json
    return r.json

def test_home_and_admin_are_separate_and_catalog_filter(client):
    home=client.get('/').text
    assert 'bot-launcher' in home and 'bot-panel' in home and '/static/home.js' in home
    assert 'preview-image' in client.get('/mesa').text
    d=client.get('/api/productos?categoria=Ferretería').json
    assert d['total']==250 and all(x['categoria']=='Ferretería' for x in d['resultados'])
    assert client.get('/api/productos?categoria=Ferretería&q=FER-0001').json['total']==1

def test_automatic_extraction_and_session_reused(app,client,monkeypatch):
    s=sesion(client)
    def fail(*a):raise AssertionError('No repetir OCR al recuperar el mismo archivo')
    monkeypatch.setattr(ia,'reconocer',fail)
    again=post(client,'/api/asistente/iniciar/'+s['extraccion']['archivo_id'],{})
    assert again.json['id']==s['id']
    restarted=crear_app(app.config['DB_PATH'].parent).test_client()
    assert restarted.get('/api/asistente/'+s['id']).json['extraccion']['id']==s['extraccion']['id']

def test_combined_summary_requires_authorization_and_executes_atomically(app,client):
    s=sesion(client);p=propuesta(client,s)
    assert p['estado']=='pendiente'
    assert post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':1,'approved':True}).status_code==409
    result=aprobar_ejecutar(client,p)
    assert result['comprobante_id'] and result['venta_id'] and result['vinculo_id']
    assert len(client.get('/api/ventas').json)==9
    assert client.get('/api/comprobantes/'+result['comprobante_id']).json['operaciones'][0]['venta_id']==result['venta_id']
    assert post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':1}).json==result
    with conectar(app.config['DB_PATH']) as db:
        assert db.execute('SELECT COUNT(*) FROM comprobantes').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM operaciones').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM ejecuciones').fetchone()[0]==1

def test_failure_does_not_leave_receipt_sale_or_money(app,client):
    s=sesion(client);p=propuesta(client,s)
    post(client,'/api/propuestas/'+p['id']+'/aprobar',{'version':1,'confirmacion':'REVISADO'})
    with conectar(app.config['DB_PATH']) as db:
        db.execute("CREATE TRIGGER falla_resumen BEFORE INSERT ON vinculos BEGIN SELECT RAISE(ABORT,'prueba'); END")
    assert post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':1}).status_code==503
    with conectar(app.config['DB_PATH']) as db:
        for tabla in ('comprobantes','operaciones','soportes_operacion','vinculos','ejecuciones'):
            assert db.execute('SELECT COUNT(*) FROM '+tabla).fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM ventas').fetchone()[0]==8

@pytest.mark.parametrize('changes',[{'confirmacion_operacion_unica':False},{'confirmacion_venta_faltante':False},{'lineas':[]},{'moneda_confirmada':None}])
def test_summary_rejects_missing_business_confirmations(client,changes):
    s=sesion(client);d=contenido(s);d['operacion'].update(changes)
    assert post(client,'/api/propuestas',{'tipo':'resolver_soporte','contenido':d}).status_code==400
    assert not client.get('/api/registros').json['comprobantes']

def test_assistant_real_loop_with_mock_selects_preparation_and_preserves_session(app,client,monkeypatch):
    s=sesion(client);calls=[]
    def mock(payload,timeout=25):
        calls.append(payload)
        assert not any(t['name'] in ('aprobar','ejecutar','preparar') for t in payload['tools'])
        if len(calls)==1:
            return {'output':[{'type':'function_call','name':'preparar_resultado','arguments':json.dumps({
                'tipo':'crear_venta','operacion_json':json.dumps(datos_venta_054(None)),
                'revision_json':None,'motivo':'Revisión final de prueba en el asistente'}),'call_id':'call1'}]}
        result=json.loads(payload['input'][-1]['output'])
        assert result['estado']=='pendiente' and result['tipo']=='resolver_soporte'
        return {'output':[{'type':'message','content':[{'type':'output_text','text':'Todo listo. Revisa el resumen y confirma para guardar.'}]}]}
    monkeypatch.setattr(ia,'respuesta_api',mock)
    r=post(client,'/api/asistente/'+s['id']+'/mensaje',{'texto':'Prepara con estos datos confirmados del escenario de prueba.'})
    assert r.status_code==200,r.json
    assert r.json['propuesta']['estado']=='pendiente' and not r.json['ocupado']
    assert len(r.json['mensajes'])==2 and len(calls)==2
    assert not client.get('/api/registros').json['comprobantes']
    restarted=crear_app(app.config['DB_PATH'].parent).test_client()
    assert restarted.get('/api/asistente/'+s['id']).json['propuesta']['id']==r.json['propuesta']['id']

def test_model_cannot_change_session_support_or_approve(app,client):
    s=sesion(client)
    with conectar(app.config['DB_PATH']) as db:
        contexto={'sesion_id':s['id'],'extraccion_id':s['extraccion']['id'],'propuesta_id':None}
        with pytest.raises(e.ErrorNegocio):agente.ejecutar_herramienta(db,'aprobar',{},contexto)
        with pytest.raises(e.ErrorNegocio):agente.ejecutar_herramienta(db,'preparar_resultado',{})

def test_failure_unlocks_session_and_keeps_no_fake_success(client,monkeypatch):
    s=sesion(client)
    def fail(*a,**kw):raise ia.ErrorIA('Fallo de API simulado')
    monkeypatch.setattr(agente,'responder',fail)
    assert post(client,'/api/asistente/'+s['id']+'/mensaje',{'texto':'Revisa el soporte'}).status_code==502
    saved=client.get('/api/asistente/'+s['id']).json
    assert not saved['ocupado'] and saved['mensajes']==[] and saved['propuesta'] is None

def test_session_rejects_concurrent_messages(app,client):
    import time
    s=sesion(client)
    with conectar(app.config['DB_PATH']) as db:
        db.execute('UPDATE sesiones_asistente SET ocupado=1,iniciado_en=?',(time.time(),))
    assert post(client,'/api/asistente/'+s['id']+'/mensaje',{'texto':'hola'}).status_code==409


def preparar_con_valores(app,s,operacion,revision=None):
    with conectar(app.config['DB_PATH']) as db:
        return agente.ejecutar_herramienta(db,'preparar_resultado',{
            'tipo':'crear_venta','operacion_json':json.dumps(operacion),
            'revision_json':json.dumps(revision) if revision else None,
            'motivo':'Revisión final con valores del negocio'},
            {'sesion_id':s['id'],'extraccion_id':s['extraccion']['id'],'propuesta_id':None})


def test_home_defaults_cop_and_document_date_preserving_ocr(app,client):
    s=sesion(client);d=datos_venta_054(None)
    d.pop('moneda_confirmada');d.pop('fecha_comercial')
    p=preparar_con_valores(app,s,d)
    assert p['estado']=='pendiente'
    assert p['contenido']['operacion']['moneda_confirmada']=='COP'
    assert p['contenido']['operacion']['fecha_comercial']==s['extraccion']['original']['document_date']
    assert p['contenido']['registro']['revision']['currency_observed'] is None
    ext=client.get('/api/extracciones/'+s['extraccion']['id']).json
    assert ext['original']['currency_observed'] is None


def test_explicit_commercial_date_is_kept(app,client):
    s=sesion(client);d=datos_venta_054(None);d['fecha_comercial']='2026-09-18'
    p=preparar_con_valores(app,s,d)
    assert p['contenido']['operacion']['fecha_comercial']=='2026-09-18'
    assert p['contenido']['registro']['revision']['document_date']=='2026-11-06'


def test_missing_document_date_requires_a_date(app,client):
    s=sesion(client);d=datos_venta_054(None);d.pop('fecha_comercial')
    revision={**s['extraccion']['original'],'document_date':None}
    with pytest.raises(e.ErrorNegocio,match='fecha comercial válida'):
        preparar_con_valores(app,s,d,revision)
    assert not client.get('/api/registros').json['propuestas']


def test_foreign_currency_is_not_silently_changed(app,client):
    s=sesion(client);d=datos_venta_054(None);d['moneda_confirmada']='USD'
    with pytest.raises(e.ErrorNegocio,match='únicamente en COP'):
        preparar_con_valores(app,s,d)


def test_consult_support_returns_business_defaults_separate_from_extraction(app,client):
    s=sesion(client)
    with conectar(app.config['DB_PATH']) as db:
        result=agente.ejecutar_herramienta(db,'consultar_soporte',{},
            {'sesion_id':s['id'],'extraccion_id':s['extraccion']['id']})
    assert result['valores_comerciales_predeterminados']=={'moneda':'COP','fecha_comercial':'2026-11-06'}
    assert result['extraccion']['original']['currency_observed'] is None


def test_cancel_clears_context_invalidates_approved_proposal_and_is_idempotent(app,client):
    s=sesion(client);p=propuesta(client,s)
    with conectar(app.config['DB_PATH']) as db:
        db.execute('UPDATE sesiones_asistente SET propuesta_id=?,mensajes=? WHERE id=?',
            (p['id'],json.dumps([{'rol':'usuario','texto':'contexto anterior'}]),s['id']))
    assert post(client,'/api/propuestas/'+p['id']+'/aprobar',{'version':1,'confirmacion':'REVISADO'}).status_code==200
    first=post(client,'/api/asistente/cancelar',{'sesion_id':s['id']})
    assert first.status_code==200 and not first.json['resultado_guardado']
    assert post(client,'/api/asistente/cancelar',{'sesion_id':s['id']}).json==first.json
    canceled=client.get('/api/propuestas/'+p['id']).json
    assert canceled['estado']=='cancelada' and canceled['version']==2
    assert post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':1}).status_code==409
    assert post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':2}).status_code==409
    assert post(client,'/api/propuestas/'+p['id']+'/aprobar',{'version':2,'confirmacion':'REVISADO'}).status_code==409
    assert client.get('/api/asistente/'+s['id']).status_code==409
    with conectar(app.config['DB_PATH']) as db:
        row=db.execute('SELECT * FROM sesiones_asistente WHERE id=?',(s['id'],)).fetchone()
        assert json.loads(row['mensajes'])==[] and row['cancelada'] and not row['ocupado']
        assert db.execute('SELECT COUNT(*) FROM ventas').fetchone()[0]==8
        assert db.execute('SELECT COUNT(*) FROM comprobantes').fetchone()[0]==0


def test_same_file_can_restart_without_canceled_history(client):
    s=sesion(client)
    post(client,'/api/asistente/cancelar',{'sesion_id':s['id']})
    again=post(client,'/api/asistente/iniciar/'+s['extraccion']['archivo_id'],{'solicitud_id':'nueva-intencion'})
    assert again.status_code==200,again.json
    assert again.json['id']!=s['id'] and again.json['mensajes']==[] and again.json['propuesta'] is None
    assert again.json['extraccion']['id']==s['extraccion']['id']


def test_cancel_before_upload_prevents_ocr(client,monkeypatch):
    assert post(client,'/api/asistente/cancelar',{'solicitud_id':'antes-de-cargar'}).status_code==200
    def fail(*a):raise AssertionError('No debe llamar OCR después de cancelar')
    monkeypatch.setattr(ia,'reconocer',fail)
    archivo=upload(client).json['archivo']
    r=post(client,'/api/asistente/iniciar/'+archivo['id'],{'solicitud_id':'antes-de-cargar'})
    assert r.status_code==409
    assert not client.get('/api/registros').json['extracciones']


def test_cancel_during_ocr_does_not_create_a_session(app,client,monkeypatch):
    def delayed(*a):
        assert post(client,'/api/asistente/cancelar',{'solicitud_id':'durante-ocr'}).status_code==200
        return lectura(148000)
    monkeypatch.setattr(ia,'reconocer',delayed)
    archivo=upload(client).json['archivo']
    r=post(client,'/api/asistente/iniciar/'+archivo['id'],{'solicitud_id':'durante-ocr'})
    assert r.status_code==409
    with conectar(app.config['DB_PATH']) as db:
        assert db.execute('SELECT COUNT(*) FROM sesiones_asistente').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM propuestas').fetchone()[0]==0


def test_cancel_during_agent_response_discards_late_tool_call(app,client,monkeypatch):
    s=sesion(client)
    def delayed(*a,**kw):
        post(client,'/api/asistente/cancelar',{'sesion_id':s['id']})
        return {'output':[{'type':'function_call','name':'preparar_resultado','call_id':'late',
            'arguments':json.dumps({'tipo':'crear_venta','operacion_json':json.dumps(datos_venta_054(None)),
                'revision_json':None,'motivo':'Respuesta que llegó después de cancelar'})}]}
    monkeypatch.setattr(ia,'respuesta_api',delayed)
    assert post(client,'/api/asistente/'+s['id']+'/mensaje',{'texto':'Prepara la propuesta'}).status_code==409
    with conectar(app.config['DB_PATH']) as db:
        assert db.execute('SELECT COUNT(*) FROM propuestas').fetchone()[0]==0
        assert db.execute('SELECT mensajes FROM sesiones_asistente WHERE id=?',(s['id'],)).fetchone()[0]=='[]'


def test_canceled_context_cannot_prepare_even_after_new_session(app,client):
    s=sesion(client)
    post(client,'/api/asistente/cancelar',{'sesion_id':s['id']})
    post(client,'/api/asistente/iniciar/'+s['extraccion']['archivo_id'],{})
    with conectar(app.config['DB_PATH']) as db:
        with pytest.raises(e.ErrorNegocio,match='cancelada'):
            agente.ejecutar_herramienta(db,'preparar_resultado',{'tipo':'crear_venta',
                'operacion_json':json.dumps(datos_venta_054(None)),'revision_json':None,'motivo':'Viejo contexto'},
                {'sesion_id':s['id'],'extraccion_id':s['extraccion']['id'],'propuesta_id':None})


def test_cancel_does_not_undo_saved_business_records(app,client):
    s=sesion(client);p=propuesta(client,s)
    with conectar(app.config['DB_PATH']) as db:
        db.execute('UPDATE sesiones_asistente SET propuesta_id=? WHERE id=?',(p['id'],s['id']))
    result=aprobar_ejecutar(client,p)
    canceled=post(client,'/api/asistente/cancelar',{'sesion_id':s['id']})
    assert canceled.json['resultado_guardado'] and canceled.json['resultado']==result
    assert client.get('/api/propuestas/'+p['id']).json['estado']=='ejecutada'
    assert len(client.get('/api/ventas').json)==9
    assert client.get('/api/comprobantes/'+result['comprobante_id']).status_code==200


def test_cancel_requires_page_token(client):
    assert client.post('/api/asistente/cancelar',json={'solicitud_id':'test'}).status_code==403


def test_sale_includes_only_its_linked_original_and_review(client):
    s=sesion(client);p=propuesta(client,s)
    result=aprobar_ejecutar(client,p)
    sale=client.get('/api/ventas/'+result['venta_id']).json
    docs=sale['vinculos'][0]['comprobantes']
    assert len(docs)==1
    doc=docs[0]
    assert doc['comprobante_id']==result['comprobante_id']
    assert doc['archivo_id']==s['extraccion']['archivo_id']
    assert doc['disponible'] and client.get(doc['original_url']).status_code==200
    assert 'nombre_guardado' not in doc
    assert client.get('/api/ventas/V-003').json['vinculos']==[]


def test_sale_marks_missing_original_instead_of_broken_preview(app,client):
    s=sesion(client);result=aprobar_ejecutar(client,propuesta(client,s))
    with conectar(app.config['DB_PATH']) as db:
        nombre=db.execute('SELECT nombre_guardado FROM archivos_ingresados WHERE id=?',(s['extraccion']['archivo_id'],)).fetchone()[0]
    (app.config['UPLOAD_DIR']/nombre).unlink()
    doc=client.get('/api/ventas/'+result['venta_id']).json['vinculos'][0]['comprobantes'][0]
    assert not doc['disponible'] and doc['original_url'] is None
    assert client.get('/archivos/'+doc['archivo_id']).status_code==409
