# Construir a partir de esta base · 120 minutos

Esta carpeta es el punto de partida estudiantil. No contiene una solución docente terminada. El docente representa al comerciante y aporta detalles ficticios desde su guía cuando el alumno pregunta. Los cambios se construyen con OpenCode por etapas pequeñas.

## 0. Abrir y comprobar · 10 minutos

Ejecutar la app, `uv run pytest -q` y explorar las ocho ventas. Buscar `134200` y observar dos candidatos. Cargar `comprobante_054.png`, abrirlo y comprobar el ID. Recargar: el archivo sigue allí. Identificar cuáles datos no se ven. No hay OCR ni registro comercial todavía.

## 1. Reconocer, revisar y registrar · 30 minutos

Pedido sugerido a OpenCode:

> Lee AGENTS.md y docs/CONTRATOS.md. Implementa el ejercicio 1 en src/ejercicios.py: cliente backend con OPENAI_OCR_MODEL=gpt-5.6-luna, prompt íntegro, salida estructurada y validación. Añade ficha editable con original visible, revisión humana explícita, persistencia y consulta del comprobante. Conserva extracción original y procedencia de correcciones. Maneja fallas y duplicados sin éxito ficticio. Explica cambios y comprueba el recorrido con mocks antes de una imagen real.

Demostrar con el 054: $148.000, 11 de septiembre de 2026, DaviPlata, destinataria particular que no se convierte en comercio, referencias ocultas y notes en null. Hora visible 12:14 p. m., precisión de minuto. Guardar solo tras revisión y volver a consultar por ID.

La carpeta docente tiene valores esperados leídos manualmente. No usarlos para responder desde la aplicación ni reemplazar una llamada real al modelo. La prueba de API debe identificarse y registrar modelo, fecha, resultado por campo y diferencias.

## 2. Buscar y asociar · 30 minutos

> Implementa las entidades y propuestas del contrato para asociar un comprobante con una venta existente. Conecta buscar_ventas como herramienta permitida, muestra candidatos con sus indicios y solicita precisión cuando haya varios. Incorpora revisión y aprobación de una propuesta exacta, idempotencia persistente y consulta posterior del vínculo. No acredites dinero bancariamente. Añade pruebas de doble confirmación, modificación de propuesta y reinicio.

Usar el 013 para candidato por monto/fecha y confirmar con el comerciante; el 022 para dos candidatos y selección expresa; el 041 para abono, sin sumar automáticamente el efectivo mencionado. Los comprobantes no tienen referencias comerciales legibles: nunca inventarlas para lograr asociación automática.

## 3. Crear la venta faltante · 35 minutos

> Implementa la creación de venta faltante mediante el agente y herramientas controladas. Pregunta por fecha comercial, productos, cantidades y precios confirmados; consulta el catálogo y calcula el total por código. Mantén borradores incompletos. Muestra propuesta versionada y espera una acción humana válida. Crea venta, líneas y vínculo en una transacción, sin tocar inventario. No permitas al modelo aprobarse ni ejecutar SQL libre. Conserva las consultas del chat inicial como regresión.

Comenzar con el 054. Buscar primero; un resultado vacío no demuestra ausencia. El comerciante confirma que falta registrar la venta y entrega las líneas de la guía docente. Comprobar total $148.000, nueva venta única y vínculo consultable tras reinicio. Distinguir financiación al usar 002 o 039.

El modelo conversacional se configura separadamente. El agente debe seleccionar herramientas y pedir datos; mantener una etiqueta clara mientras el chat siga siendo determinista. Si el grupo necesita más tiempo, completar el recorrido comercial con controles de la interfaz y terminar el bucle de herramientas como práctica posterior, sin afirmar que el agente ya está listo.

## 4. Demostrar y cerrar · 15 minutos

- Doble carga del mismo archivo: un ID.
- Doble confirmación: un solo efecto comercial (prueba por implementar).
- Dos candidatos: pedir selección.
- Venta parcial: no equiparar pago con total de venta.
- Reinicio: recuperar imagen, comprobante, venta y relación.
- Error de API: mostrar fallo, sin datos inventados ni cambios comerciales.

La base inicial solo aprueba pruebas de su infraestructura. Añadir pruebas significativas de cada capacidad implementada y una demostración manual. Casos de total oculto, factura de transporte, referencia de factura explícita, nueva foto del mismo soporte y texto malicioso necesitan fixtures adicionales: los 12 soportes seleccionados no cubren todo el universo de aceptación.
