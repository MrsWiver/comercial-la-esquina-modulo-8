# Contratos y límites del proyecto inicial

## Capas que ya funcionan

- `src/db.py`: SQL parametrizado, conexiones con claves foráneas activas y totales calculados.
- `src/app.py`: API local, validación PNG/JPEG con Pillow, hash SHA-256, archivo temporal + renombre atómico, exclusión de duplicados por restricción UNIQUE y transacción `BEGIN IMMEDIATE`.
- `archivos_ingresados`: evidencia cargada, sin datos extraídos. No equivale a comprobante, operación o dinero recibido.
- `mensajes_chat`: conversación de práctica. No es una bitácora de autorizaciones.
- Protección de escrituras: token de página y comprobación de origen. Host limitado a localhost. La interfaz usa textContent al mostrar datos externos.

El modelo no está conectado. Las rutas de ejercicio responden 501 hasta sustituir los puntos de extensión. Son contratos de arranque, no una API comercial terminada.

## API implementada

| Ruta | Resultado |
| --- | --- |
| GET `/api/resumen` | Conteos reales y modo `practica_sin_ia` |
| GET `/api/productos?q=arroz&pagina=1` | 30 filas por página y total encontrado |
| GET `/api/ventas?q=V-001&importe=130700&fecha=2026-05-11` | Filtros opcionales combinados; máximo 100 candidatos |
| GET `/api/ventas/V-001` | Líneas, precios y total calculado |
| GET/POST `/api/archivos` | Lista / carga multipart con campo `archivo` |
| GET `/archivos/ARC-…` | Evidencia original desde registro persistente |
| GET `/api/casos` | Nombres y URLs de los 12 ejemplos; no incluye respuestas docentes |
| GET/POST `/api/chat` | Historial / consulta JSON `{ "texto": "ventas 134200" }` |

Todas las escrituras requieren el encabezado `X-Practica-Token` que usa el frontend. Límites: 1.000 caracteres por mensaje, 100 mensajes recuperados, 8 MB por imagen y 24 millones de píxeles. No habilitar CORS abierto ni compartir la app en Internet.

## Ejercicio 1 · Extraer y registrar

`extraer_soporte(archivo, db)` recibe el registro interno ya validado; resuelve la ruta desde el almacén. Nunca permite rutas arbitrarias provenientes del modelo. Ruta inicial: POST `/api/extraer/<archivo_id>`.

Implementar un cliente backend que lea `OPENAI_API_KEY` y `OPENAI_OCR_MODEL` desde configuración privada; la primera versión no carga `.env`. Usar exactamente `gpt-5.6-luna`. Conservar `prompts/extractor-v1.txt` sin modificar. Adjuntar el contrato `prompts/extraccion-v1.schema.json` como salida estructurada y verificar qué subconjunto admite la API vigente. Validar además fechas reales y significado: JSON válido no basta.

El esquema es una propuesta v1 del taller. Incluye clasificación desconocida como null; alternativas de instrumento; moneda explícita y estado observado; todas las referencias separadas; evidencia textual y confianza por campo. `time_precision=minute` implica segundos normalizados `00`; nunca fueron observados. No inventar zona horaria. La fecha de carga UTC vive por separado.

Reglas semánticas para probar al implementar:

- `amount_basis=missing` exige `total_amount=null`. Un desglose puede poblar `inferred_amount`, separado y advertido.
- Addi/Sistecrédito usan `financed_value`; no registrar como dinero recibido.
- `stated_cash_amount` no se suma al envío. Las menciones en una conversación no prueban otro pago.
- Si no hay comercio identificado o texto económico legible, `merchant_or_store` y `notes` son null.
- Fechas ambiguas y referencias ocultas permanecen null; IDs de referencia son texto con ceros iniciales.
- Un `expense` no permite cobrar ni asociar automáticamente como ingreso.
- Confianza es evaluación del extractor, no probabilidad de autenticidad.

`registrar_comprobante(datos, db)`, POST `/api/comprobantes`, debe recibir una revisión humana explícita. Crear tablas de comprobantes y correcciones, conservar extracción original inmutable, campos corregidos, origen de la corrección y eventos. Consultar después el nuevo registro desde la app con GET por ID y mostrar imagen, lectura y estado. Eso todavía está pendiente.

## Ejercicios 2 y 3 · Propuestas y efectos

`preparar_operacion(datos, db)`, POST `/api/propuestas`, produce propuesta persistente con ID, versión, tipo de operación, datos exactos, evidencia y estado `pendiente`. No ejecuta. Una persona debe revisar el contenido concreto en la interfaz y aprobar esa versión. Crear una ruta de aprobación que emita un registro en servidor. Un booleano del cliente o del modelo no sustituye ese paso.

`registrar_operacion_aprobada(datos, db)`, POST `/api/propuestas/ejecutar`, recibe ID/versión, valida la aprobación, revalida datos y ejecuta una sola vez en una transacción. Guardar clave idempotente UNIQUE, resultado y eventos. Si la propuesta cambia, invalidar su aprobación; si la respuesta de escritura es incierta, consultar por propuesta antes de repetir.

Entidades por implementar:

| Entidad | Datos mínimos y relación |
| --- | --- |
| Comprobante | Archivo, extracción original, revisión y estado de extracción |
| Operación reportada | Naturaleza (cobro/financiación/gasto), monto y moneda, referencias, estado financiero `no_verificado` |
| Soporte de operación | Varios archivos pueden describir una operación; no duplicar dinero |
| Vínculo comercial | Operación, venta, importe aplicado positivo, aprobado por propuesta; una venta admite varios abonos |
| Propuesta | ID, versión, contenido exacto, estado, revisión/aprobación y resultado idempotente |
| Evento | Carga, edición, aprobación, ejecución o falla; sin claves ni datos personales innecesarios |

El primer taller puede limitar una operación a una venta. Una segunda imagen del mismo documento requiere comparación de referencias/contexto y posible revisión: el hash solo detecta archivos idénticos. Estados de revisión, asociación y verificación financiera se conservan por separado.

Crear venta: pedir fecha comercial, productos, cantidades y precios confirmados. Consultar el catálogo; total por código, no por aritmética del modelo. Cliente y factura externa pueden quedar ausentes cuando no son necesarios; nunca inferirlos. Generar un ID interno distinto de una factura externa. Si faltan líneas, mantener borrador. No actualizar inventario. La creación y su vínculo aprobado deben ser atómicos.

## Agente conversacional

El chat inicial es explícitamente determinista. Al ampliarlo, el modelo debe elegir herramientas permitidas (buscar, consultar catálogo, pedir datos, preparar) y usar sus resultados. No presentar reglas `if/else` como razonamiento de un agente. No dar SQL arbitrario, rutas de disco ni capacidad de autoaprobarse. Separar modelo conversacional de `OPENAI_OCR_MODEL`; elegir y configurar el primero de manera explícita. Limitar pasos (por ejemplo 6), tiempo, tamaño de entradas y reintentos. Conservar propuestas entre reinicios; no confiar en memoria del proceso.

## Recuperación y migraciones

La semilla es portable y nunca lee el módulo 3 al arrancar. El esquema inicial tiene `PRAGMA user_version=1`. Al ampliar, añadir migraciones versionadas; `CREATE TABLE IF NOT EXISTS` no actualiza bases existentes.

La escritura del archivo y SQLite son dos operaciones distintas. La base renombra el original antes del commit; limpia temporales/huérfanos al iniciar y comunica evidencia ausente sin fingir éxito. Ejecutar una sola instancia por carpeta. El reinicio respaldado incluye DB, chat e imágenes; las futuras tablas también deben vivir en esa SQLite para entrar en el respaldo.
