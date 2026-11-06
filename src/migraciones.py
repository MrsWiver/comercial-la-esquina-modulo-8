"""Migraciones transaccionales; nunca reemplazan la semilla ni el estado existente."""
DDL = [
'''CREATE TABLE extracciones (
 id TEXT PRIMARY KEY, archivo_id TEXT NOT NULL UNIQUE REFERENCES archivos_ingresados(id),
 original TEXT NOT NULL, modelo TEXT NOT NULL, creado_en TEXT NOT NULL,
 origen TEXT NOT NULL CHECK(origen IN ('api_real','mock_prueba')),
 prompt_sha256 TEXT NOT NULL)''',
'''CREATE TABLE propuestas (
 id TEXT PRIMARY KEY, version INTEGER NOT NULL CHECK(version>0), tipo TEXT NOT NULL,
 contenido TEXT NOT NULL, estado TEXT NOT NULL CHECK(estado IN ('borrador','pendiente','aprobada','ejecutada')),
 creado_en TEXT NOT NULL, resultado TEXT)''',
'''CREATE TABLE aprobaciones (
 id TEXT PRIMARY KEY, propuesta_id TEXT NOT NULL REFERENCES propuestas(id),
 version INTEGER NOT NULL, contenido_sha256 TEXT NOT NULL, creado_en TEXT NOT NULL,
 UNIQUE(propuesta_id,version))''',
'''CREATE TABLE comprobantes (
 id TEXT PRIMARY KEY, extraccion_id TEXT NOT NULL UNIQUE REFERENCES extracciones(id),
 revision TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'revisado',
 propuesta_id TEXT NOT NULL UNIQUE REFERENCES propuestas(id), creado_en TEXT NOT NULL)''',
'''CREATE TABLE correcciones (
 id INTEGER PRIMARY KEY, comprobante_id TEXT NOT NULL REFERENCES comprobantes(id),
 campo TEXT NOT NULL, original TEXT NOT NULL, corregido TEXT NOT NULL,
 origen TEXT NOT NULL CHECK(origen='revision_humana'), motivo TEXT NOT NULL)''',
'''CREATE TABLE operaciones (
 id TEXT PRIMARY KEY, naturaleza TEXT NOT NULL CHECK(naturaleza IN ('cobro','financiacion','gasto')),
 monto INTEGER NOT NULL CHECK(monto>0), moneda TEXT NOT NULL CHECK(moneda='COP'),
 referencias TEXT NOT NULL, estado_financiero TEXT NOT NULL DEFAULT 'no_verificado'
 CHECK(estado_financiero='no_verificado'))''',
'''CREATE TABLE soportes_operacion (
 comprobante_id TEXT PRIMARY KEY REFERENCES comprobantes(id),
 operacion_id TEXT NOT NULL REFERENCES operaciones(id))''',
'''CREATE TABLE vinculos (
 id TEXT PRIMARY KEY, operacion_id TEXT NOT NULL UNIQUE REFERENCES operaciones(id),
 venta_id TEXT NOT NULL REFERENCES ventas(id), importe INTEGER NOT NULL CHECK(importe>0),
 propuesta_id TEXT NOT NULL UNIQUE REFERENCES propuestas(id))''',
'''CREATE TABLE ejecuciones (
 clave TEXT PRIMARY KEY, propuesta_id TEXT NOT NULL UNIQUE REFERENCES propuestas(id),
 resultado TEXT NOT NULL, creado_en TEXT NOT NULL)''',
'''CREATE TABLE eventos (
 id INTEGER PRIMARY KEY, entidad_id TEXT NOT NULL, tipo TEXT NOT NULL,
 detalle TEXT NOT NULL, creado_en TEXT NOT NULL)''',
'''CREATE TRIGGER extraccion_inmutable_update BEFORE UPDATE ON extracciones
 BEGIN SELECT RAISE(ABORT,'Extracción inmutable'); END''',
'''CREATE TRIGGER extraccion_inmutable_delete BEFORE DELETE ON extracciones
 BEGIN SELECT RAISE(ABORT,'Extracción inmutable'); END''',
]


def migrar(db):
    db.execute('BEGIN IMMEDIATE')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version > 3:
        raise RuntimeError('Base creada por una versión posterior de la aplicación.')
    if version == 1:
        for sql in DDL:
            db.execute(sql)
        db.execute('PRAGMA user_version=2')
        version=2
    if version == 2:
        db.execute("ALTER TABLE mensajes_chat ADD COLUMN origen TEXT NOT NULL DEFAULT 'determinista' CHECK(origen IN ('determinista','agente_ia'))")
        db.execute('PRAGMA user_version=3')
    db.commit()
