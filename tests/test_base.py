import hashlib
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
import pytest
from PIL import Image
from src.app import crear_app
from src.db import ROOT, conectar

@pytest.fixture
def app(tmp_path):
    app=crear_app(tmp_path/'practica');app.config['TESTING']=True
    return app
@pytest.fixture
def client(app):return app.test_client()
def headers(client):
    return {'X-Practica-Token':re.search(r'name="practica-token" content="([^"]+)"',client.get('/').text)[1]}
def image_bytes(format='PNG'):
    out=io.BytesIO();Image.new('RGB',(12,12),'red').save(out,format=format)
    return out.getvalue()
def upload(client,raw=None,name='prueba.png'):
    return client.post('/api/archivos',data={'archivo':(io.BytesIO(raw if raw is not None else image_bytes()),name)},headers=headers(client))

def test_seed_totals_catalog_and_integrity(app,client):
    assert client.get('/api/resumen').json=={'productos':1250,'ventas':8,'archivos':0,'modo':'practica_sin_ia','version':'0.1.0'}
    expected={v['id']:sum(l['cantidad']*l['precio_unitario'] for l in v['lineas']) for v in json.loads((ROOT/'datos/semilla/ventas.json').read_text())}
    with conectar(app.config['DB_PATH']) as db:
        assert not db.execute('pragma foreign_key_check').fetchall()
        assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
        assert db.execute('select count(*) from inventario').fetchone()[0]==827
        assert db.execute('select count(*) from proveedores').fetchone()[0]==75
        assert 'correo' not in {r[1] for r in db.execute('pragma table_info(proveedores)')}
        assert not db.execute('select 1 from venta_lineas l join productos p on l.producto_codigo=p.codigo where l.precio_unitario!=p.precio_venta').fetchall()
    assert {v['id']:v['total'] for v in client.get('/api/ventas').json}==expected

def test_ambiguous_partial_missing_and_different_date(client):
    assert [v['id'] for v in client.get('/api/ventas?importe=134200').json]==['V-003','V-004']
    assert client.get('/api/ventas?importe=19400').json==[]
    assert client.get('/api/ventas/V-006').json['total']==100000
    assert client.get('/api/ventas/V-008').json['fecha_comercial']=='2026-09-17'
    for amount in (158100,30000,118700,280000,148000):
        assert client.get(f'/api/ventas?importe={amount}').json==[]

def test_filters_detail_and_sql_input(client):
    v=client.get('/api/ventas/V-001').json
    assert v['total']==sum(l['subtotal'] for l in v['lineas'])==130700
    assert v['factura_externa'] is None
    assert len(client.get('/api/ventas?q=V-001&fecha=2026-05-11&importe=130700').json)==1
    assert client.get('/api/ventas?q=%27%20OR%201%3D1--').json==[]
    assert client.get('/api/ventas/NO').status_code==404
    assert client.get('/api/ventas?importe=1.2').status_code==400
    assert client.get('/api/ventas?fecha=2026-02-30').status_code==400
    assert client.get('/api/productos?pagina=0').status_code==400

def test_products_pagination(client):
    first=client.get('/api/productos').json;second=client.get('/api/productos?pagina=2').json
    assert first['total']==1250 and len(first['resultados'])==30
    assert not {p['codigo'] for p in first['resultados']} & {p['codigo'] for p in second['resultados']}
    rows=client.get('/api/productos?q=FER-0001').json
    assert rows['total']==1 and rows['resultados'][0]['precio_venta']==121300

def test_upload_duplicate_persistence_and_original(app,client):
    raw=image_bytes();r=upload(client,raw)
    assert r.status_code==201 and not r.json['duplicado']
    f=r.json['archivo'];assert f['estado']=='pendiente_reconocimiento'
    assert f['sha256']==hashlib.sha256(raw).hexdigest()
    again=upload(client,raw,name='otra.png')
    assert again.status_code==200 and again.json['duplicado']
    assert again.json['archivo']['id']==f['id']
    restarted=crear_app(app.config['DB_PATH'].parent).test_client()
    assert len(restarted.get('/api/archivos').json)==1
    assert restarted.get('/archivos/'+f['id']).data==raw
    assert len(client.get('/api/ventas').json)==8

def test_concurrent_upload_is_single_effect(app,client):
    h=headers(client);raw=image_bytes()
    def call(_):
        with app.test_client() as c:
            return c.post('/api/archivos',headers=h,data={'archivo':(io.BytesIO(raw),'x.png')}).json
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(call,range(2)))
    assert len({r['archivo']['id'] for r in results})==1
    assert sum(r['duplicado'] for r in results)==1
    assert len(client.get('/api/archivos').json)==1

@pytest.mark.parametrize('raw,name',[(b'not image','x.png'),(image_bytes(),'x.pdf'),(image_bytes(),'x.jpg'),(image_bytes()[:30],'x.png')])
def test_bad_images_rejected(client,raw,name):
    assert upload(client,raw,name).status_code==400
    assert client.get('/api/archivos').json==[]

def test_jpeg_supported(client):
    r=upload(client,image_bytes('JPEG'),'x.jpeg')
    assert r.status_code==201 and r.json['archivo']['mime']=='image/jpeg'

def test_oversized_rejected(client):
    assert upload(client,b'x'*(8*1024*1024+1)).status_code==413
    assert client.get('/api/archivos').json==[]

def test_pixel_limit_rejected(client,monkeypatch):
    monkeypatch.setattr(Image,'MAX_IMAGE_PIXELS',50)
    assert upload(client).status_code==400

def test_disk_failure_rolls_back(app,client,monkeypatch):
    def fail(*a):raise OSError('fallo simulado')
    monkeypatch.setattr('src.app.os.replace',fail)
    assert upload(client).status_code==503
    assert client.get('/api/archivos').json==[]
    assert list(app.config['UPLOAD_DIR'].iterdir())==[]

def test_recovery_orphans_and_missing_evidence(app,client):
    f=upload(client).json['archivo'];folder=app.config['UPLOAD_DIR']
    orphan=folder/('a'*64+'.png');orphan.write_bytes(b'orphan')
    part=folder/'interrupted.part';part.write_bytes(b'part')
    restarted=crear_app(folder.parent).test_client()
    assert not orphan.exists() and not part.exists()
    assert restarted.get('/archivos/'+f['id']).status_code==200
    (folder/f['nombre_guardado']).unlink()
    assert restarted.get('/archivos/'+f['id']).status_code==409
    assert upload(restarted).status_code==409

def test_chat_uses_database_and_persists(app,client):
    r=client.post('/api/chat',json={'texto':'ventas 134200'},headers=headers(client))
    assert 'V-003' in r.json['respuesta'] and 'V-004' in r.json['respuesta']
    assert 'por sí solo' in r.json['respuesta']
    restarted=crear_app(app.config['DB_PATH'].parent).test_client()
    assert len(restarted.get('/api/chat').json)==2
    r=client.post('/api/chat',json={'texto':'crea una venta'},headers=headers(client))
    assert 'no lenguaje libre' in r.json['respuesta']
    assert len(client.get('/api/ventas').json)==8

def test_csrf_and_origin(client):
    assert client.post('/api/chat',json={'texto':'ventas'}).status_code==403
    assert client.post('/api/chat',json={'texto':'ventas'},headers={**headers(client),'Origin':'https://externo.example'}).status_code==403
    assert client.get('/',headers={'Host':'evil.example'}).status_code==400

@pytest.mark.parametrize('endpoint',['/api/comprobantes','/api/propuestas','/api/propuestas/ejecutar'])
def test_class_extension_has_no_fake_success(client,endpoint):
    r=client.post(endpoint,json={'approved':True},headers=headers(client))
    assert r.status_code in (400,404,409) and 'error' in r.json
    assert len(client.get('/api/ventas').json)==8

def test_ocr_without_key_does_not_invent(client,monkeypatch):
    monkeypatch.setattr('src.ia.configuracion',lambda:{'OPENAI_API_KEY':'','OPENAI_OCR_MODEL':'gpt-5.6-luna','OPENAI_CHAT_MODEL':'gpt-5.6-luna'})
    f=upload(client).json['archivo']
    r=client.post('/api/extraer/'+f['id'],headers=headers(client))
    assert r.status_code==502 and 'total_amount' not in r.json
    assert client.post('/api/extraer/missing',headers=headers(client)).status_code==404

def test_twelve_examples_and_hashes(client):
    fixtures=json.loads((ROOT/'soportes/manifest.json').read_text())
    assert len(client.get('/api/casos').json)==len(fixtures)==12
    for f in fixtures:
        image=client.get('/soportes/'+f['archivo'])
        assert image.status_code==200
        assert hashlib.sha256(image.data).hexdigest()==f['sha256']
    assert client.get('/soportes/no.png').status_code==404

def test_extraction_schema_contract():
    schema=json.loads((ROOT/'prompts/extraccion-v1.schema.json').read_text())
    assert schema['$schema']=='https://json-schema.org/draft/2020-12/schema'
    def check_object(node):
        if node.get('type')=='object':
            assert set(node['required'])==set(node['properties'])
            assert node['additionalProperties'] is False
            for child in node['properties'].values():check_object(child)
    check_object(schema)
    assert schema['additionalProperties'] is False
    assert len(schema['properties']['references']['required'])==11
    assert 'gpt-5.6-luna' in (ROOT/'.env.example').read_text()


def test_original_prompt_is_preserved():
    assert hashlib.sha256((ROOT/'prompts/extractor-v1.txt').read_bytes()).hexdigest()=='9559d1c8ff92a5f293a0e0dea5509db4165a1b40fb638e7aca9cd16dcab2e170'
