PRAGMA foreign_keys = ON;
CREATE TABLE proveedores (id TEXT PRIMARY KEY, razon_social TEXT NOT NULL, categoria TEXT);
CREATE TABLE productos (
 codigo TEXT PRIMARY KEY, nombre TEXT NOT NULL, categoria TEXT NOT NULL,
 proveedor_id TEXT NOT NULL REFERENCES proveedores(id), unidad TEXT,
 precio_costo INTEGER NOT NULL CHECK(precio_costo >= 0),
 precio_venta INTEGER NOT NULL CHECK(precio_venta >= 0)
);
CREATE TABLE inventario (
 id INTEGER PRIMARY KEY, producto_codigo TEXT NOT NULL REFERENCES productos(codigo),
 ubicacion TEXT, lote TEXT NOT NULL, stock INTEGER NOT NULL CHECK(stock >= 0),
 stock_minimo INTEGER NOT NULL CHECK(stock_minimo >= 0), fecha_vencimiento TEXT,
 estado TEXT, ultima_actualizacion TEXT, observaciones TEXT, fila_origen INTEGER NOT NULL,
 UNIQUE(producto_codigo,lote)
);
CREATE TABLE ventas (
 id TEXT PRIMARY KEY, fecha_comercial TEXT NOT NULL,
 cliente TEXT, factura_externa TEXT, moneda TEXT NOT NULL DEFAULT 'COP' CHECK(moneda='COP'),
 origen TEXT NOT NULL DEFAULT 'practica_ficticia'
);
CREATE TABLE venta_lineas (
 id INTEGER PRIMARY KEY, venta_id TEXT NOT NULL REFERENCES ventas(id),
 producto_codigo TEXT NOT NULL REFERENCES productos(codigo),
 cantidad INTEGER NOT NULL CHECK(cantidad>0),
 precio_unitario INTEGER NOT NULL CHECK(precio_unitario>=0),
 UNIQUE(venta_id,producto_codigo)
);
-- El total de venta siempre se calcula con SQL. No hay un total editable.
CREATE VIEW resumen_ventas AS
 SELECT v.*, SUM(l.cantidad*l.precio_unitario) AS total,
 COUNT(l.id) AS numero_lineas FROM ventas v JOIN venta_lineas l ON l.venta_id=v.id GROUP BY v.id;
-- Infraestructura de carga. No son comprobantes revisados ni pagos.
CREATE TABLE archivos_ingresados (
 id TEXT PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE,
 nombre_original TEXT NOT NULL, nombre_guardado TEXT NOT NULL UNIQUE,
 mime TEXT NOT NULL CHECK(mime IN ('image/png','image/jpeg')),
 bytes INTEGER NOT NULL CHECK(bytes>0), cargado_en TEXT NOT NULL,
 estado TEXT NOT NULL DEFAULT 'pendiente_reconocimiento' CHECK(estado='pendiente_reconocimiento')
);
CREATE TABLE mensajes_chat (
 id INTEGER PRIMARY KEY, rol TEXT NOT NULL CHECK(rol IN ('usuario','asistente')),
 texto TEXT NOT NULL, creado_en TEXT NOT NULL
);
-- Las tablas comerciales de comprobantes, operaciones, propuestas, vínculos y
-- eventos se diseñan en clase. Ver docs/CONTRATOS.md. No confundir archivo con pago.
PRAGMA user_version = 1;
