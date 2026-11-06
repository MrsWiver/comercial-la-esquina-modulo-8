"""Fixtures inventados y API simulada. No son lecturas reales ni usan docente/."""
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from PIL import Image
from src.app import crear_app
from src.db import conectar, ROOT, construir
from src import ejercicios as e, ia, agente
from test_base import headers, upload
RECONOCER_REAL=ia.reconocer


def lectura(monto=134200):
    schema=e.SCHEMA
    def nulo(node):
        t=node.get('type')
        if t=='object':return {k:nulo(v) for k,v in node['properties'].items()}
        if t=='array':return []
        return None
    r=nulo(schema)
    r.update(document_type='transfer',amount_basis='observed_total',total_amount=monto,
             document_date='2026-11-06',document_time='12:14:00',time_precision='minute')
    return r


@pytest.fixture
def app(tmp_path,monkeypatch):
    app=crear_app(tmp_path/'practica');app.config.update(TESTING=True,OCR_ORIGEN='mock_prueba')
    monkeypatch.setattr(ia,'reconocer',lambda *a:lectura())
    return app


@pytest.fixture
def client(app):return app.test_client()


def post(c,url,data):return c.post(url,json=data,headers=headers(c))


def extraer(c):
    f=upload(c).json['archivo']
    r=post(c,'/api/extraer/'+f['id'],{})
    assert r.status_code==200,r.json
    return r.json


def aprobar_ejecutar(c,p):
    a=post(c,'/api/propuestas/'+p['id']+'/aprobar',{'version':p['version'],'confirmacion':'REVISADO'})
    assert a.status_code==200,a.json
    result=post(c,'/api/propuestas/ejecutar',{'id':p['id'],'version':p['version']})
    assert result.status_code==200,result.json
    return result.json


def comprobante(c,revision=None):
    ext=extraer(c)
    p=post(c,'/api/comprobantes',{'extraccion_id':ext['id'],'revision':revision or ext['original'],'motivo':'Verificado en original inventado de prueba'})
    assert p.status_code==200,p.json
    return aprobar_ejecutar(c,p.json)['comprobante_id']


def asociacion(c,cid,venta='V-003',importe=134200):
    return post(c,'/api/propuestas',{'tipo':'asociar','contenido':{'comprobante_id':cid,'venta_id':venta,
        'moneda_confirmada':'COP','importe_aplicado':importe,'confirmacion_operacion_unica':True}})


def test_review_provenance_corrections_immutable_and_restart(app,client):
    ext=extraer(client)
    assert ext['origen']=='mock_prueba' and ext['original']['currency_observed'] is None
    r=dict(ext['original']);r['notes']='Corrección humana inventada para probar auditoría'
    cid=comprobante(client,r)
    c=client.get('/api/comprobantes/'+cid).json
    assert c['extraccion']['original']['notes'] is None
    assert c['correcciones'][0]['campo']=='notes'
    assert c['correcciones'][0]['origen']=='revision_humana'
    with conectar(app.config['DB_PATH']) as db:
        with pytest.raises(Exception,match='inmutable'):
            db.execute('UPDATE extracciones SET original=?',('{}',))
    restarted=crear_app(app.config['DB_PATH'].parent).test_client()
    assert restarted.get('/api/comprobantes/'+cid).json['revision']['notes']==r['notes']


def test_approval_is_required_and_model_boolean_cannot_authorize(client):
    cid=comprobante(client);p=asociacion(client,cid).json
    r=post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':1,'approved':True})
    assert r.status_code==409
    assert len(client.get('/api/ventas').json)==8
    assert client.get('/api/registros').json['operaciones']==[]


def test_partial_link_single_effect_and_restart(app,client):
    cid=comprobante(client);p=asociacion(client,cid,'V-006',19400).json
    result=aprobar_ejecutar(client,p)
    again=post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':1})
    assert again.json==result
    sale=client.get('/api/ventas/V-006').json
    assert sale['total']==100000 and len(sale['vinculos'])==1 and sale['vinculos'][0]['importe']==19400
    assert result['estado_financiero']=='no_verificado'
    restarted=crear_app(app.config['DB_PATH'].parent).test_client()
    assert restarted.get('/api/comprobantes/'+cid).json['operaciones'][0]['venta_id']=='V-006'


def test_edit_invalidates_approval_and_versions(client):
    cid=comprobante(client);p=asociacion(client,cid).json
    assert post(client,'/api/propuestas/'+p['id']+'/aprobar',{'version':1,'confirmacion':'REVISADO'}).status_code==200
    changed={**p,'contenido':{**p['contenido'],'venta_id':'V-004'}}
    updated=post(client,'/api/propuestas',changed)
    assert updated.status_code==200 and updated.json['version']==2 and updated.json['estado']=='pendiente'
    assert post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':1}).status_code==409
    assert post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':2}).status_code==409
    assert post(client,'/api/propuestas',changed).status_code==409
    result=aprobar_ejecutar(client,updated.json)
    assert result['venta_id']=='V-004'


def test_concurrent_execution_single_effect(app,client):
    cid=comprobante(client);p=asociacion(client,cid).json
    post(client,'/api/propuestas/'+p['id']+'/aprobar',{'version':1,'confirmacion':'REVISADO'})
    h=headers(client)
    def call(_):
        with app.test_client() as c:return c.post('/api/propuestas/ejecutar',json={'id':p['id'],'version':1},headers=h)
    with ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(call,range(2)))
    assert all(x.status_code==200 for x in r) and r[0].json==r[1].json
    assert len(client.get('/api/ventas/V-003').json['vinculos'])==1


def test_new_sale_atomic_catalog_inventory_unchanged(app,client):
    cid=comprobante(client)
    with conectar(app.config['DB_PATH']) as db:
        before=[tuple(x) for x in db.execute('SELECT * FROM inventario')]
    contenido={'comprobante_id':cid,'moneda_confirmada':'COP','importe_aplicado':121300,
        'confirmacion_operacion_unica':True,'confirmacion_venta_faltante':True,'fecha_comercial':'2026-11-06',
        'cliente':None,'factura_externa':None,'lineas':[{'producto_codigo':'FER-0001','cantidad':1,'precio_unitario':121300}]}
    p=post(client,'/api/propuestas',{'tipo':'crear_venta','contenido':contenido})
    assert p.status_code==200,p.json
    result=aprobar_ejecutar(client,p.json)
    sale=client.get('/api/ventas/'+result['venta_id']).json
    assert sale['total']==121300 and sale['cliente'] is None and len(sale['vinculos'])==1
    assert len(client.get('/api/ventas').json)==9
    with conectar(app.config['DB_PATH']) as db:
        assert before==[tuple(x) for x in db.execute('SELECT * FROM inventario')]


def test_transaction_failure_rolls_back_everything(app,client):
    cid=comprobante(client);p=asociacion(client,cid).json
    post(client,'/api/propuestas/'+p['id']+'/aprobar',{'version':1,'confirmacion':'REVISADO'})
    with conectar(app.config['DB_PATH']) as db:
        db.execute("CREATE TRIGGER falla BEFORE INSERT ON vinculos BEGIN SELECT RAISE(ABORT,'fallo simulado'); END")
    assert post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':1}).status_code==503
    assert client.get('/api/registros').json['operaciones']==[]
    assert client.get('/api/propuestas/'+p['id']).json['estado']=='aprobada'


@pytest.mark.parametrize('cambio',[{'document_date':'2026-02-30'},{'amount_basis':'missing'}, {'document_time':'12:14:22'}, {'document_type':'addi_credit'}, {'references':{'receipt':12}}])
def test_semantic_errors_preserve_no_extraction(app,client,monkeypatch,cambio):
    r=lectura();r.update(cambio);monkeypatch.setattr(ia,'reconocer',lambda *a:r)
    f=upload(client).json['archivo']
    assert post(client,'/api/extraer/'+f['id'],{}).status_code==400
    assert client.get('/api/registros').json['extracciones']==[]


def test_fraction_is_preserved_but_blocks_registration(client,monkeypatch):
    monkeypatch.setattr(ia,'reconocer',lambda *a:lectura(134200.25))
    ext=extraer(client)
    assert ext['original']['total_amount']==134200.25
    r=post(client,'/api/comprobantes',{'extraccion_id':ext['id'],'revision':ext['original'],'motivo':'Revisión de fracción'})
    assert r.status_code==409


def test_financing_and_mentioned_cash_separate(client,monkeypatch):
    r=lectura();r.update(document_type='addi_credit',amount_basis='financed_value',stated_cash_amount=90000)
    monkeypatch.setattr(ia,'reconocer',lambda *a:r)
    cid=comprobante(client);p=asociacion(client,cid).json
    assert p['contenido']['naturaleza']=='financiacion' and p['contenido']['monto']==134200
    result=aprobar_ejecutar(client,p)
    assert client.get('/api/comprobantes/'+cid).json['operaciones'][0]['naturaleza']=='financiacion'


def test_draft_survives_restart_and_cannot_approve(app,client):
    p=post(client,'/api/propuestas',{'tipo':'crear_venta','borrador':True,'contenido':{'lineas':[]}}).json
    r=post(client,'/api/propuestas/'+p['id']+'/aprobar',{'version':1,'confirmacion':'REVISADO'})
    assert r.status_code==409
    c=crear_app(app.config['DB_PATH'].parent).test_client()
    assert c.get('/api/propuestas/'+p['id']).json['estado']=='borrador'


def test_api_failure_no_fake_data(client,monkeypatch):
    def fail(*a):raise ia.ErrorIA('Fallo simulado')
    monkeypatch.setattr(ia,'reconocer',fail)
    f=upload(client).json['archivo']
    assert post(client,'/api/extraer/'+f['id'],{}).status_code==502
    assert client.get('/api/registros').json['comprobantes']==[]


def test_agent_selects_tools_and_cannot_execute(app,client,monkeypatch):
    calls=[]
    def mock(payload,timeout=25):
        calls.append(payload)
        if len(calls)==1:return {'output':[{'type':'function_call','name':'buscar_ventas','arguments':json.dumps({'texto':'','importe':134200,'fecha':None}),'call_id':'call1'}]}
        result=json.loads(payload['input'][-1]['output'])
        assert {x['id'] for x in result}=={'V-003','V-004'}
        return {'output':[{'type':'message','content':[{'type':'output_text','text':'Hay dos candidatos. ¿Cuál confirmó el comerciante?'}]}]}
    monkeypatch.setattr(ia,'respuesta_api',mock)
    r=post(client,'/api/agente',{'texto':'Busca una venta por 134200'})
    assert r.status_code==200 and 'dos candidatos' in r.json['respuesta'] and len(calls)==2
    with conectar(app.config['DB_PATH']) as db:
        with pytest.raises(e.ErrorNegocio):agente.ejecutar_herramienta(db,'ejecutar',{'approved':True})


def test_private_configuration_and_payload(client,monkeypatch,tmp_path):
    captured=[]
    monkeypatch.setattr(ia,'configuracion',lambda:{'OPENAI_API_KEY':'secret','OPENAI_OCR_MODEL':'gpt-5.6-luna','OPENAI_CHAT_MODEL':'gpt-5.6-luna'})
    # Inspección del contrato sin red, claves ni respuestas docentes.
    def response(payload,timeout=25):
        captured.append(payload)
        return {'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(lectura())}]}]}
    monkeypatch.setattr(ia,'respuesta_api',response)
    # El cliente original se conserva como referencia antes de instalar el fixture.
    f=tmp_path/'x.png';f.write_bytes(b'fake-test-image')
    RECONOCER_REAL(f,'image/png')
    assert captured[0]['model']=='gpt-5.6-luna'
    assert captured[0]['instructions'].startswith((ROOT/'prompts/extractor-v1.txt').read_text())
    assert captured[0]['text']['format']['strict'] is True
    assert 'secret' not in client.get('/api/configuracion').text


def segundo_archivo(c):
    out=io.BytesIO();Image.new('RGB',(13,13),'blue').save(out,format='PNG')
    r=c.post('/api/archivos',data={'archivo':(io.BytesIO(out.getvalue()),'segunda.png')},headers=headers(c))
    assert r.status_code==201
    ext=post(c,'/api/extraer/'+r.json['archivo']['id'],{}).json
    p=post(c,'/api/comprobantes',{'extraccion_id':ext['id'],'revision':ext['original'],'motivo':'Segunda foto inventada de prueba'})
    return aprobar_ejecutar(c,p.json)['comprobante_id']


def test_duplicate_reference_requires_attachment_without_new_money(client,monkeypatch):
    r=lectura();r['references']['transfer_reference']='000123'
    monkeypatch.setattr(ia,'reconocer',lambda *a:r)
    c1=comprobante(client);p=asociacion(client,c1).json;result=aprobar_ejecutar(client,p)
    c2=segundo_archivo(client)
    assert asociacion(client,c2).status_code==409
    p2=post(client,'/api/propuestas',{'tipo':'adjuntar_soporte','contenido':{'comprobante_id':c2,
        'operacion_id':result['operacion_id'],'confirmacion_mismo_documento':True}})
    assert p2.status_code==200,p2.json
    aprobar_ejecutar(client,p2.json)
    assert len(client.get('/api/registros').json['operaciones'])==1
    assert client.get('/api/comprobantes/'+c2).json['operaciones'][0]['id']==result['operacion_id']
    assert client.get('/api/comprobantes/'+c1).json['revision']['references']['transfer_reference']=='000123'


def test_approved_sale_revalidates_catalog_and_rolls_back(app,client):
    cid=comprobante(client)
    d={'comprobante_id':cid,'moneda_confirmada':'COP','importe_aplicado':121300,'confirmacion_operacion_unica':True,
       'confirmacion_venta_faltante':True,'fecha_comercial':'2026-11-06','cliente':None,'factura_externa':None,
       'lineas':[{'producto_codigo':'FER-0001','cantidad':1,'precio_unitario':121300}]}
    p=post(client,'/api/propuestas',{'tipo':'crear_venta','contenido':d}).json
    post(client,'/api/propuestas/'+p['id']+'/aprobar',{'version':1,'confirmacion':'REVISADO'})
    with conectar(app.config['DB_PATH']) as db:db.execute("UPDATE productos SET precio_venta=120000 WHERE codigo='FER-0001'")
    assert post(client,'/api/propuestas/ejecutar',{'id':p['id'],'version':1}).status_code==400
    assert len(client.get('/api/ventas').json)==8 and not client.get('/api/registros').json['operaciones']


def test_expense_can_be_reviewed_but_not_associated(client,monkeypatch):
    r=lectura();r['document_type']='expense';monkeypatch.setattr(ia,'reconocer',lambda *a:r)
    cid=comprobante(client)
    assert asociacion(client,cid).status_code==400


def test_unknown_currency_requires_confirmation(client):
    cid=comprobante(client)
    d={'comprobante_id':cid,'venta_id':'V-003','importe_aplicado':134200,'confirmacion_operacion_unica':True}
    assert post(client,'/api/propuestas',{'tipo':'asociar','contenido':d}).status_code==400


def test_agent_limit_and_history_origin(client,monkeypatch):
    def mock(payload,timeout=25):
        return {'output':[{'type':'function_call','name':'consultar_catalogo','arguments':'{"texto":"FER-0001"}','call_id':'call'+str(len(payload['input']))}]}
    monkeypatch.setattr(ia,'respuesta_api',mock)
    r=post(client,'/api/agente',{'texto':'Consulta el catálogo'})
    assert r.status_code==200 and 'límite' in r.json['respuesta']
    historia=client.get('/api/chat').json
    assert all(x['origen']=='agente_ia' for x in historia)
    post(client,'/api/chat',{'texto':'ventas'})
    assert client.get('/api/chat').json[-1]['origen']=='determinista'
    assert len(client.get('/api/ventas').json)==8


def test_migration_preserves_existing_chat_and_files(tmp_path):
    base=tmp_path/'negocio.sqlite3';construir(base)
    with conectar(base) as db:
        db.execute("INSERT INTO mensajes_chat(rol,texto,creado_en) VALUES('usuario','historia previa','2026-11-06')")
        assert db.execute('PRAGMA user_version').fetchone()[0]==1
    app=crear_app(tmp_path)
    with conectar(base) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==3
        assert db.execute('SELECT origen FROM mensajes_chat').fetchone()[0]=='determinista'
    assert app.test_client().get('/api/chat').json[0]['texto']=='historia previa'


def test_api_http_error_does_not_echo_key(monkeypatch):
    import urllib.error
    monkeypatch.setattr(ia,'configuracion',lambda:{'OPENAI_API_KEY':'private-secret'})
    def fail(*a,**kw):raise urllib.error.HTTPError('https://api.openai.com',401,'private-secret',{},None)
    monkeypatch.setattr(ia.urllib.request,'urlopen',fail)
    with pytest.raises(ia.ErrorIA) as exc:ia.respuesta_api({'model':'gpt-5.6-luna','input':'test'})
    assert '401' in str(exc.value) and 'private-secret' not in str(exc.value)


def test_delivery_is_clean_with_twelve_authorized_examples(tmp_path):
    import zipfile,sqlite3
    from scripts.empaquetar import empaquetar
    zip_path=empaquetar(tmp_path/'entrega.zip')
    with zipfile.ZipFile(zip_path) as z:
        names=z.namelist()
        assert len([n for n in names if n.endswith('.png')])==12
        assert 'proyecto-inicial/backend/.env.example' in names
        assert not any(n.endswith('/.env') or '.venv/' in n or '__pycache__/' in n or '/respaldos/' in n for n in names)
        z.extract('proyecto-inicial/datos/practica/negocio.sqlite3',tmp_path)
    with sqlite3.connect(tmp_path/'proyecto-inicial/datos/practica/negocio.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM ventas').fetchone()[0]==8
        for tabla in ('archivos_ingresados','mensajes_chat','extracciones','comprobantes','propuestas','operaciones','vinculos'):
            assert db.execute('SELECT COUNT(*) FROM '+tabla).fetchone()[0]==0


def datos_venta_054(cid):
    return {'comprobante_id':cid,'moneda_confirmada':'COP','importe_aplicado':148000,
        'confirmacion_operacion_unica':True,'confirmacion_venta_faltante':True,
        'fecha_comercial':'2026-09-11','cliente':None,'factura_externa':None,
        'lineas':[{'producto_codigo':'FER-0001','cantidad':1,'precio_unitario':121300},
                  {'producto_codigo':'FER-0222','cantidad':1,'precio_unitario':26700}]}


@pytest.mark.parametrize('borrador_modelo',[True,False])
def test_agent_complete_first_preparation_is_pending_without_approval(app,client,monkeypatch,borrador_modelo):
    monkeypatch.setattr(ia,'reconocer',lambda *a:lectura(148000))
    cid=comprobante(client)
    with conectar(app.config['DB_PATH']) as db:
        aprobaciones=db.execute('SELECT COUNT(*) FROM aprobaciones').fetchone()[0]
        propuesta=agente.ejecutar_herramienta(db,'preparar',{'tipo':'crear_venta',
            'contenido_json':json.dumps(datos_venta_054(cid)),'borrador':borrador_modelo,'id':None,'version':None})
        assert propuesta['estado']=='pendiente' and propuesta['version']==1
        assert propuesta['contenido']['total']==148000 and propuesta['resultado'] is None
        assert db.execute('SELECT COUNT(*) FROM aprobaciones').fetchone()[0]==aprobaciones
        assert db.execute('SELECT COUNT(*) FROM ventas').fetchone()[0]==8
        assert db.execute('SELECT COUNT(*) FROM operaciones').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM vinculos').fetchone()[0]==0
    assert post(client,'/api/propuestas/ejecutar',{'id':propuesta['id'],'version':1}).status_code==409


@pytest.mark.parametrize('cambio',[{'lineas':[]},{'confirmacion_venta_faltante':False},
    {'confirmacion_operacion_unica':False},{'moneda_confirmada':None},
    {'lineas':[{'producto_codigo':'FER-0001','cantidad':1,'precio_unitario':1}]}])
def test_agent_incomplete_or_invalid_remains_draft(app,client,monkeypatch,cambio):
    monkeypatch.setattr(ia,'reconocer',lambda *a:lectura(148000))
    cid=comprobante(client);contenido={**datos_venta_054(cid),**cambio}
    with conectar(app.config['DB_PATH']) as db:
        propuesta=agente.ejecutar_herramienta(db,'preparar',{'tipo':'crear_venta',
            'contenido_json':json.dumps(contenido),'borrador':True,'id':None,'version':None})
        assert propuesta['estado']=='borrador'
    assert post(client,'/api/propuestas/'+propuesta['id']+'/aprobar',{'version':1,'confirmacion':'REVISADO'}).status_code==409


def test_manual_complete_draft_is_preserved(client,monkeypatch):
    monkeypatch.setattr(ia,'reconocer',lambda *a:lectura(148000))
    cid=comprobante(client)
    p=post(client,'/api/propuestas',{'tipo':'crear_venta','contenido':datos_venta_054(cid),'borrador':True})
    assert p.status_code==200 and p.json['estado']=='borrador'
