# Comprobantes desde el detalle de venta · 6 de noviembre de 2026

`uv run pytest -q`: **85 pruebas aprobadas**. El detalle de venta incluye los comprobantes realmente vinculados a cada operación, con nombre de archivo, vista previa, apertura del original y acceso a la revisión. No se infieren relaciones por monto ni fecha. Se verifica un soporte por venta, varios soportes para la misma operación y ausencia del original en disco sin fingir disponibilidad. La respuesta pública no expone nombres internos de almacenamiento.

Recorrido de lectura comprobado en la interfaz de la base existente: Ventas → V-002 → Comprobantes asociados → Ver comprobante; se abrió comprobante_013.png, vinculado a su cobro de 22000. El diálogo conserva el detalle de venta debajo y permite abrir el original en otra pestaña. No se modificaron asociaciones, ventas ni datos y no se hicieron llamadas al modelo.

---

# Cancelación de soporte u operación · 6 de noviembre de 2026

`uv run pytest -q`: **83 pruebas aprobadas**. Se verifican cancelación idempotente de una propuesta previamente aprobada, invalidación de versión y aprobación, rechazo de ejecución/edición posterior, limpieza de mensajes y bloqueo, nueva conversación limpia con el mismo archivo y conservación de operaciones ya ejecutadas. También se prueban cancelación antes de cargar, durante OCR y mientras responde el agente: no se crean sesión/propuesta tardías ni se restauran mensajes. El endpoint exige token local.

Recorrido visual con mocks y SQLite temporal en localhost:8020: cargar 054, aportar líneas ficticias, obtener resumen pendiente, pulsar Cancelar, observar desaparición de adjunto/resumen y confirmación de cancelación, recargar y comprobar conversación inicial vacía. No se ejecutó la propuesta. No hubo nuevas llamadas reales a OpenAI ni cancelaciones sobre datos comerciales del usuario.

La evidencia y extracciones originales no se eliminan físicamente; se descarta su contexto en el bot. La migración v5 conserva datos previos. Las peticiones externas ya enviadas pueden concluir, pero la cancelación impide reactivar contexto, preparar operaciones o guardar mensajes tardíos. Si una operación ya terminó de guardarse, se informa y se conserva.

---

# Valores comerciales predeterminados · 6 de noviembre de 2026

Por instrucción del usuario, COP es la moneda fija del negocio y la fecha documental se usa como fecha comercial predeterminada al crear una venta. El agente deja de solicitar esos datos cuando ya están disponibles. Las herramientas aplican los valores en servidor, tanto para el chat de la mesa como para el bot de la home; se conserva la extracción original y currency_observed=null si la moneda no era explícita. Una fecha comercial indicada por el usuario prevalece, y una fecha ilegible requiere consulta. Una moneda extranjera explícita no se convierte silenciosamente.

`uv run pytest -q`: **75 pruebas aprobadas**. Regresiones nuevas verifican valores ausentes, conservación del OCR, fecha explícita distinta, ausencia de fecha, rechazo de moneda extranjera y contexto del soporte separado de los valores comerciales.

Recorrido de interfaz con mocks en una base aislada: adjuntar 054, respuesta sin pedir moneda ni fecha, aportar únicamente confirmación de venta faltante/operación única y líneas ficticias, y obtener resumen pendiente con COP y fecha 2026-09-11. La herramienta simulada omitió moneda y fecha en su preparación: el servidor las completó. No se confirmó ni ejecutó la propuesta, ni se hicieron llamadas reales adicionales a OpenAI. La conversación previa del usuario no se reescribió.

---

# Home y asistente flotante · 6 de noviembre de 2026

`uv run pytest -q`: **70 pruebas aprobadas**. JavaScript de home y mesa verificado con node --check; git diff --check sin errores.

Nueva ruta `/` con catálogo real y bot flotante; la mesa permanece en `/mesa`. Pruebas nuevas cubren filtros comerciales, reutilización de extracción/sesión, persistencia del chat, herramientas acotadas a la sesión, rechazo de autoaprobación, fallo de API sin éxito ficticio, recuperación del bloqueo, confirmación requerida y ejecución compuesta idempotente. Una falla inyectada al escribir el vínculo revierte también comprobante, operación y venta nueva. Se rechazan propuestas completas sin datos/confirmaciones comerciales válidos.

QA de interfaz con API simulada en una base temporal, servidor localhost:8020. Se eligió el ejemplo 054: adjuntar inició extracción/conversación; el bot pidió datos faltantes; con líneas ficticias FER-0001 y FER-0222 mostró resumen de 148000. Una sola confirmación guardó comprobante, venta, operación y vínculo en la base temporal y mostró el resultado final. Al recargar se recuperó conversación y resultado. Las respuestas indicaban expresamente «Prueba simulada»; no son una nueva extracción real.

Se observó la home en escritorio y el bot a 375 × 812. Se corrigió su ancho para quedar dentro del área visible con barras de desplazamiento. Original accesible desde el chat, resultado sin paneles de validación técnica, foco visible, teclado y estilos con reducción de movimiento. No se hizo auditoría completa con lector de pantalla ni prueba en teléfono físico. La interfaz real quedó abierta sin enviar nuevos soportes a OpenAI ni ejecutar operaciones comerciales en la base de trabajo.

La migración v4 conserva datos previos y añade sesiones. Los cambios en la transacción compuesta no eliminan revisión, aprobación humana en servidor, versión/hash, límites monetarios ni idempotencia. La experiencia nueva fue probada con mocks; las pruebas reales previas del OCR y agente no se presentan como validación real integral de este flujo nuevo.

---

# Corrección y repetición real del agente · 6 de noviembre de 2026

Se aclararon las instrucciones y el contrato de la herramienta preparar: pendiente significa esperar aprobación, no autorización. Además, la herramienta del agente valida el contenido en servidor; si es completo y válido lo prepara como pendiente incluso si el modelo envía borrador=true. Los datos incompletos o no válidos siguen en borrador cuando se solicitó conservarlos. La acción manual Guardar borrador mantiene su comportamiento. Nunca se genera aprobación ni ejecución por esta normalización.

`uv run pytest -q`: **58 pruebas aprobadas**. Las regresiones verifican primera preparación completa con ambos valores de borrador emitidos por el modelo, total calculado, ausencia de nuevas aprobaciones y efectos comerciales, rechazo de ejecución sin aprobación, y conservación de borradores sin líneas, sin confirmaciones, sin moneda o con precio incorrecto. También se verifica que el borrador manual completo sigue siendo borrador.

Se repitió la prueba con llamadas reales de gpt-5.6-luna en una copia nueva aislada usando la extracción real del 054 y un fixture sintético de revisión únicamente en la copia. El primer turno consultó comprobante y ventas por importe/fecha y amplió criterios; no encontró venta identificable y pidió datos. En el segundo turno recibió los mismos datos comerciales ficticios de la guía docente y consultó el catálogo.

**Resultado:** una única llamada a preparar creó `PROP-8d370525e3ee4d9f`, versión 1, tipo crear_venta, estado pendiente, total e importe aplicado 148000, resultado null. Se consultó por ID y se comprobó el estado en SQLite. No hubo turno adicional para corregir el estado, ni edición posterior de la propuesta. El modelo envió borrador=false en esta llamada real; la corrección del caso borrador=true se verifica en la regresión automatizada.

Recorrido observado en la interfaz de la copia aislada: Registros → propuesta → versión 1, pendiente, dos líneas (121300 + 26700), total 148000, aprobación sin marcar. No se aprobó ni ejecutó. La base de trabajo conservó ocho ventas, cero comprobantes, propuestas, operaciones y vínculos. La propuesta de esta prueba pertenece solo a la copia aislada.

Traza completa y conversación: `datos/practica/prueba-agente-054-corregido.json`, fuera de Git y ZIP. Se conservó la evidencia anterior, incluido su fallo inicial, como registro histórico. La prueba con un caso no garantiza la elección correcta de datos por el modelo en todos los escenarios; las validaciones y la aprobación humana siguen siendo obligatorias.

---

# Prueba real del agente · 6 de noviembre de 2026

Modelo `gpt-5.6-luna`, tres turnos reales, sin mocks de API. Se usó una copia SQLite aislada de la práctica con la extracción real del 054. La revisión/registro del comprobante se preparó como fixture sintético **solo en la copia**: no se atribuye a una autorización humana real y no se tocó el registro comercial de la base de trabajo.

El agente consultó el comprobante y ejecutó buscar_ventas con importe/fecha, solo importe, solo fecha y sin filtros. No identificó una venta compatible y solicitó datos, sin inferir productos ni cliente.

Para el segundo turno se aportaron expresamente los datos comerciales ficticios del escenario docente del 054 (no como datos extraídos por OCR): fecha 2026-09-11, cliente de práctica, factura externa null, FER-0001 × 1 a 121300 y FER-0222 × 1 a 26700. Consultó el catálogo; la consulta inicial con dos códigos juntos no devolvió coincidencias, por lo que separó las búsquedas. Comprobó precios y preparó/consultó un borrador completo.

**Limitación observada:** el segundo turno dejó `borrador=true` aunque se pidió una propuesta completa pendiente. Su respuesta sugirió revisar/aprobar desde la interfaz, pero los borradores no se pueden aprobar. Se requirió un tercer turno explícito para pedir su actualización con borrador=false y comprobar el estado real.

Resultado verificado directamente en SQLite y consultado por el agente: `PROP-fcf9e9c662d049c9`, tipo crear_venta, versión 2, estado pendiente, total e importe aplicado 148000, resultado null. Sin aprobaciones comerciales, operaciones ni vínculos; ocho ventas en la copia. No se ejecutó la propuesta.

La base de trabajo conservó ocho ventas, cero comprobantes, propuestas, operaciones y vínculos. La propuesta de prueba **no aparece en la base de trabajo**. La traza completa de herramientas, argumentos, resultados y conversación está en `datos/practica/prueba-agente-054.json`, excluido de Git y de los ZIP. Los datos de la guía docente se usaron solo como escenario comercial ficticio; no reemplazaron lecturas de la API.

La prueba valida búsqueda y preparación mediante herramientas reales, con la corrección conversacional indicada. No valida ejecución comercial ni demuestra que el agente siempre elija el estado correcto al primer intento.

---

# Prueba OCR real · 6 de noviembre de 2026

Una llamada real autorizada a OpenAI mediante la ruta de extracción de la aplicación, con `gpt-5.6-luna` y `comprobante_054.png`. HTTP local 200, duración 11,82 segundos. Extracción persistente `EXT-b3ef0035e44643e9`, origen `api_real`, consultada nuevamente desde la API. Prompt original conservado. Sin mocks y sin usar docente/ como respuesta. La clave permaneció en backend/.env y no se incluyó en informes.

Comparación con la imagen original:

| Campo | Resultado real | Comparación visual |
| --- | --- | --- |
| Tipo y medio | transfer / DAVIPLATA | Correcto |
| Total observado | 148000 | Correcto |
| Fecha documental | 2026-09-11 | Correcto |
| Hora | 12:14:00, precisión minute | Correcto; segundos normalizados, no visibles |
| Estado visible | Transacción exitosa | Correcto; no verifica recepción bancaria |
| Moneda | null | Correcto; el símbolo $ no identifica por sí solo una moneda |
| Comercio y notas | null | Correcto; la destinataria particular no se convierte en comercio |
| Referencias | Todas null | Correcto; están ocultas |
| Importe inferido y efectivo mencionado | null | Correcto |

Diferencias de evidencia textual: `observed_text.document_type` resume «Transferencia DaviPlata», mientras que la imagen dice «Pasaste Plata a otro DaviPlata»; `observed_text.time_precision` describe «Solo minutos visibles», que es una evaluación y no una cita literal. Los campos estructurados principales coinciden; la fidelidad literal de esos campos de evidencia necesita revisión. No se corrigió silenciosamente la extracción original.

La evidencia completa y comparación por campo se guardaron en `datos/practica/prueba-api-054.json`, excluido de Git y del ZIP. No se aprobó ni ejecutó un registro de comprobante, operación, vínculo o venta. La imagen quedó disponible para revisión humana en Registros.

Esta prueba valida una extracción real. El agente conversacional, los demás soportes y las operaciones comerciales con respuestas reales de IA siguen sin validación real integral. El registro inferior documenta el estado previo a esta prueba y las pruebas simuladas.

---

# Validación de la ampliación · 6 de noviembre de 2026

`uv run pytest -q`: **50 pruebas aprobadas** en el entorno local. `node --check static/app.js` y `git diff --check` sin errores.

Además de la infraestructura original, se verifican: revisión y correcciones con procedencia humana, extracción inmutable, monedas sin inferencia, precisión de minuto, fracciones sin redondeo, aprobación requerida, rechazo de approved=true como autorización, invalidación al editar, versión obsoleta, doble ejecución concurrente con un efecto, revalidación del catálogo, rollback sin efectos parciales, financiación separada de efectivo mencionado, pagos parciales, segunda fotografía adjunta sin duplicar dinero, duplicidad de referencias con ceros iniciales, borradores y recuperación después de reiniciar, herramientas permitidas y límites del agente, origen de mensajes, errores sin claves, migraciones sobre datos existentes y ZIP limpio.

## Pruebas de interfaz de esta ampliación

Se usó un servidor de pruebas aislado en localhost:8018 con SQLite temporal y `origen=mock_prueba`. El mock devolvió campos inventados con una advertencia explícita; no leyó el soporte ni consumió la API. Las imágenes utilizadas eran ejemplos autorizados. No se usó docente/ para fabricar una respuesta.

Recorridos observados en navegador:

- Cargar ejemplo, reconocer con mock, ver original, modificar/confirmar revisión, preparar registro, aprobar versión y ejecutar.
- Buscar 134200, ver V-003 y V-004, seleccionar V-003 expresamente, preparar asociación, aprobar y ejecutar; recargar y recuperar comprobante y vínculo.
- Crear una venta de prueba con FER-0001, cantidad 1, precio de catálogo 121300; comprobar total calculado, aprobación, ejecución y consulta de venta con vínculo `no_verificado`.
- Resumen con nueve ventas en la base temporal al crear la venta. La semilla y el inventario no cambiaron.

La captura del detalle de la venta corresponde únicamente a esa prueba simulada. No demuestra datos extraídos de la imagen ni verificación bancaria. El recorrido se observó en el panel adaptable del navegador; no se hizo una auditoría completa con lector de pantalla ni prueba en dispositivo físico.

## Estado previo a la prueba real del 054

No hay una clave API configurada en este entorno. **No se hicieron llamadas reales a OpenAI**. No se verificó disponibilidad del modelo `gpt-5.6-luna` para esta cuenta ni su aceptación efectiva del esquema enviado. Se conservó exactamente el modelo solicitado para OCR y agente, sin fallback.

La integración usa Responses API y los contratos oficiales consultados de imágenes, salida estructurada y function calling. Sus payloads, errores y bucle de herramientas se comprobaron con respuestas simuladas; esto no reemplaza la prueba real.

Para cerrar la validación de IA: configurar backend/.env, enviar un único soporte autorizado desde la interfaz, registrar fecha/modelo, comparar por campo con el original y documentar diferencias antes de continuar. Los escenarios de texto malicioso, total oculto y referencias ambiguas requieren ampliar evidencia real; no se declaran ejercicios de IA aprobados por haber pasado mocks.

El prompt conserva el SHA-256 original `9559d1c8ff92a5f293a0e0dea5509db4165a1b40fb638e7aca9cd16dcab2e170`. No se modificaron imágenes autorizadas, semilla, docente/ ni proyecto/materiales del módulo 3. El ZIP probado incluye una SQLite limpia migrada a v3, ocho ventas y cero archivos, mensajes, extracciones, comprobantes, propuestas, operaciones o vínculos; excluye claves, respaldos y cachés.

---

## Evidencia histórica de la base inicial

El registro inferior describe la base anterior a esta ampliación; sus menciones de ejercicios pendientes corresponden a ese estado histórico.

# Validación de la base inicial

Preparación: 30 de octubre de 2026. Entorno local macOS, Python 3.14.7, dependencias fijadas por uv.lock.

## Pruebas automatizadas

`uv run pytest -q`: **24 pruebas aprobadas**.

Cubren datos e integridad SQLite, sumas desde líneas, precios del catálogo, filtros parametrizados, dos candidatos, abono, ventas ausentes, fechas distintas, paginación, persistencia de chat y archivos, PNG/JPEG, archivos inválidos, límites de bytes y píxeles, duplicados concurrentes, falla de disco, recuperación de huérfanos y evidencia ausente, protección de origen/token, integridad del prompt, consistencia estructural del esquema y funciones de clase con respuesta 501.

La prueba del esquema comprueba estructura del contrato y campos requeridos; no es una prueba del validador de la API. La validación completa de respuestas y reglas semánticas se construye con el ejercicio 1.

## Recorrido manual en navegador

Comprobado en el navegador de la app:

- Mesa de trabajo visible con 1.250 productos y ocho ventas.
- Vista Ventas, filtro 134200: aparecen V-003 y V-004.
- Apertura de V-003: líneas FER-0012 y FER-0064, total 134200.
- Vista Soportes: aparecen los 12 ejemplos.
- Carga del 054 desde el selector de ejemplos: se conserva imagen e ID ARC y queda «pendiente de reconocimiento».
- Consulta del chat `ventas 134200`: dos candidatos y explicación de que el importe no demuestra relación.
- Recarga del navegador: conserva conversación e imagen con el mismo ID.
- Segunda carga del 054: un solo archivo; el mismo ID y aviso de duplicado.

Se observó el diseño de escritorio y el diseño adaptable en un panel de aproximadamente 632 píxeles. No se hizo una auditoría completa con lector de pantalla ni una prueba física en teléfono de 375 píxeles. La interfaz incluye etiquetas, foco visible, navegación por botones, diálogo nativo y reducción de movimiento.

Los datos generados al probar la UI se retiran del estado inicial mediante reinicio respaldado. El ZIP se construye desde una semilla nueva, independientemente del estado local. Se comprueba también la extracción del ZIP y la reconstrucción sin acceder al proyecto del módulo 3.

## Conservación de fuentes

Se comparó el SHA-256 de SQLite del módulo 3 con el valor anotado al preparar la semilla: sin cambios. El prompt de la app coincide byte a byte con el prompt del material del módulo 8. Los 12 archivos conservan los hashes de las copias anonimizadas.

## Pendientes explícitos

No se hicieron llamadas reales a OpenAI. OCR, agente conversacional, revisión/registro de comprobantes, propuestas, aprobación comercial y creación/asociación de ventas son ejercicios pendientes. Tampoco se declaró verificación bancaria. No hay pruebas aprobadas de esas funciones, ni solución docente completa. El repositorio público distribuye la base estudiantil y los ejemplos autorizados.
