# Contratos de la aplicación ampliada

Implementación local para un operador. Las escrituras requieren `X-Practica-Token` emitido al cargar la página y origen local. El modelo carece de herramientas de aprobación/ejecución. Un `approved=true` no tiene efecto.

## Consultas e infraestructura

Se conservan resumen, catálogo paginado, búsqueda de ventas, líneas calculadas, carga PNG/JPEG con Pillow, límite de 8 MB y 24 millones de píxeles, SHA-256, persistencia y recuperación de archivos. No hay SQL libre ni rutas de archivo provenientes del modelo. El inventario no se modifica.

| Ruta | Contrato |
| --- | --- |
| GET `/api/resumen` | Conteos y modo del chat de comandos `practica_sin_ia`; no indica que el agente optativo esté deshabilitado |
| GET `/api/configuracion` | Modelos y booleano de clave configurada; nunca devuelve la clave |
| GET `/api/productos?q=…&pagina=1` | Catálogo, 30 filas por página |
| GET `/api/ventas?q=…&importe=…&fecha=…` | Filtros combinados, hasta 100 candidatos |
| GET `/api/ventas/<id>` | Líneas, total calculado y vínculos con naturaleza y estado financiero |
| GET/POST `/api/archivos` | Lista / carga multipart con campo `archivo` |
| GET `/archivos/<id>` | Original; 409 si falta evidencia |
| GET `/api/casos` | Solo nombres y URLs de ejemplos; sin respuestas docentes |
| GET/POST `/api/chat` | Historial persistente / comandos deterministas `{texto}` |
| POST `/api/agente` | `{texto}`; Responses API con herramientas permitidas |
| GET `/api/registros` | Hasta 100 extracciones, comprobantes, propuestas y operaciones |

El historial conserva `origen=determinista` o `agente_ia`. El resumen mantiene el contrato previo del chat de comandos. La activación de IA se hace expresamente en la interfaz. El agente y el OCR se configuran por separado, ambos con `gpt-5.6-luna` por decisión del usuario.

## Extracción y revisión

POST `/api/extraer/<archivo_id>` resuelve el original desde SQLite, no acepta rutas arbitrarias y usa `prompts/extractor-v1.txt` íntegro, con esquema de salida estructurada v1. El cliente usa HTTPS a Responses API con `store=false`, timeout, límite de salida y errores que no exponen credenciales. Una extracción ya guardada se reutiliza sin otra llamada.

La validación local comprueba JSON Schema, fechas existentes, precisión de hora, montos ausentes y financiación. La lectura conserva modelo, fecha UTC de procesamiento, hash del prompt y origen `api_real`. Mocks solo se instalan desde pruebas en bases aisladas, con origen `mock_prueba`; no existe un selector de mocks en la API pública.

GET `/api/extracciones/<id>` devuelve original y comprobante asociado, si existe. La extracción original es inmutable en SQLite. Hora documental sin zona horaria; la carga y el procesamiento tienen su propia fecha UTC.

POST `/api/comprobantes` recibe `{extraccion_id, revision, motivo}` y **prepara una propuesta**, no escribe todavía un comprobante. La interfaz exige revisión del original. Se debe aprobar y ejecutar la propuesta con el procedimiento inferior. GET `/api/comprobantes/<id>` consulta original, revisión, correcciones y vínculos después de ejecutar.

Las referencias conservan texto y ceros iniciales. Las ausencias son null. Una fracción en cualquier monto original o revisado impide registrar el comprobante: se conserva la extracción para revisar el diseño monetario. Las correcciones guardan campo, valor original, nuevo valor, motivo y `revision_humana`.

## Propuestas y autorización

POST `/api/propuestas` recibe:

```json
{"tipo":"asociar","contenido":{"comprobante_id":"CMP-…","venta_id":"V-003","importe_aplicado":134200,"moneda_confirmada":"COP","confirmacion_operacion_unica":true}}
```

Tipos permitidos: `registrar_comprobante`, `asociar`, `crear_venta`, `adjuntar_soporte`. La revisión del comprobante puede prepararse con `/api/comprobantes`.

- `crear_venta` requiere fecha_comercial, cliente y factura_externa como texto o null, líneas por producto_codigo/cantidad/precio_unitario y confirmacion_venta_faltante. Los precios deben coincidir con catálogo; el servidor calcula total. Cliente, factura y productos nunca se infieren del pago.
- `adjuntar_soporte` requiere comprobante_id, operacion_id y confirmacion_mismo_documento; compara monto, naturaleza y moneda. No añade dinero.
- `borrador=true` permite conservar una asociación o venta incompleta. No puede aprobarse.
- Para editar, enviar `id` y `version` actual, tipo y contenido. Incrementa versión, vuelve a pendiente/borrador e invalida la aprobación anterior. Una ejecutada es inmutable.

GET `/api/propuestas/<id>` consulta contenido exacto, versión, estado y resultado.

POST `/api/propuestas/<id>/aprobar`, `{version, confirmacion:"REVISADO"}`, es una acción humana separada en la interfaz. El servidor revalida el contenido y guarda un registro de aprobación con versión y hash del contenido. La ruta no está entre las herramientas del agente. El booleano de singularidad es una declaración de revisión, no una autorización de ejecución.

POST `/api/propuestas/ejecutar`, `{id, version}`, exige la aprobación emitida por el servidor y revalida precios, saldos, comprobantes y referencias. Usa `BEGIN IMMEDIATE`, clave de ejecución UNIQUE por propuesta/versión y resultado persistente. Repetir la misma ejecución devuelve ese resultado, incluso tras reiniciar. Si cambia la versión o el contenido, la aprobación anterior no sirve.

Crear venta, líneas, operación, soporte y vínculo ocurre en una sola transacción. Una falla revierte todos los efectos. Si la respuesta se pierde, consultar la propuesta antes de reintentar.

## Operaciones y alcance

Una operación admite varios soportes y un vínculo a una venta. Una venta admite varios abonos. Importe aplicado positivo y limitado por monto observado y saldo comercial. La financiación se identifica separadamente del cobro. El efectivo mencionado no se suma. Gastos o documentos sin clasificar no pueden asociarse como ingreso.

Referencias coincidentes (excepto factura) bloquean otra operación y remiten a revisión/adjuntar. El hash no identifica una segunda foto del mismo documento; cuando faltan referencias se requiere comparación y confirmación humana. No se declara autenticidad ni recepción bancaria: `estado_financiero=no_verificado` siempre.

## Agente y recuperación

Herramientas: buscar ventas, consultar catálogo/venta/comprobante/propuesta y preparar propuestas comerciales o borradores. No hay extracción masiva, aprobación, ejecución, SQL libre ni navegación. En la herramienta preparar del agente, un contenido completo y válido se guarda como pendiente incluso si el modelo marca borrador=true; únicamente los contenidos incompletos/no válidos permanecen en borrador cuando se solicita conservarlos. Esta normalización no aprueba ni ejecuta y no cambia la opción manual Guardar borrador. Máximo seis llamadas a herramientas/seis pasos y presupuesto de 90 segundos por turno, con timeout de red acotado. Historial de 20 mensajes como contexto; conversación recuperable hasta 100 mensajes. Los borradores y propuestas viven en SQLite, no en memoria del modelo.

Migraciones: v1 infraestructura, v2 tablas comerciales y trigger de extracción inmutable, v3 origen del historial. Se aplican en transacción y conservan datos. Una versión futura se rechaza. Respaldo y reinicio incluyen la carpeta completa.

Implementación basada en los contratos de [salida estructurada](https://developers.openai.com/api/docs/guides/structured-outputs), [herramientas](https://developers.openai.com/api/docs/guides/function-calling) e [imágenes](https://developers.openai.com/api/docs/guides/images-vision). El OCR se comprobó con una llamada real del soporte 054 en esta cuenta; el agente con herramientas y los otros escenarios siguen pendientes de validación real. No se cambia de modelo automáticamente.
