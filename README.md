# Comercial La Esquina · Módulo 8

App local de aprendizaje para leer soportes, revisar sus datos y relacionarlos con ventas. Incluye extracción mediante OpenAI, agente con herramientas controladas y operaciones comerciales con revisión y aprobación humana. **OCR validado con una llamada real y el soporte 054 (6 de noviembre de 2026). El agente también se probó con llamadas reales en una copia aislada: búsqueda y propuesta completa pendiente desde la primera preparación, sin ejecución. Los demás escenarios no tienen validación real integral.**

## Iniciar

Requiere Python 3.11 o superior y uv.

```bash
uv sync --locked
uv run python -m scripts.iniciar_datos
uv run python -m src.app
```

Abre http://127.0.0.1:8008. Para detener, usa Ctrl+C. La base existente se conserva y se migra al iniciar; no se reemplaza automáticamente.

## Home y asistente flotante

La página inicial está en `/`; el sistema completo sigue en `/mesa`. La cabecera muestra «Sistema de gestión» y una barra de accesos directos a Mesa de trabajo, Ventas, Productos y precios, Soportes y Registros y propuestas, también en móvil. Desde la mesa puedes volver mediante «Inicio comercial». La home muestra el catálogo real, búsqueda por nombre/código, filtros por categoría y el asistente abajo a la derecha, adaptable a móvil.

Adjuntar un PNG/JPEG inicia automáticamente su extracción y la conversación con el agente. El bot consulta el soporte y las ventas; si faltan productos o confirmaciones comerciales, los pregunta. La moneda comercial es siempre COP y la fecha de la nueva venta toma por defecto la fecha de la transacción leída del comprobante; solo se pide fecha si no es legible, y se respeta otra fecha indicada por la persona. No muestra pantallas de validación ni llamadas a herramientas. Al tener los datos completos presenta el original y un resumen final con **Confirmar y guardar**.

Esa única acción humana aprueba la versión revisada y permite registrar el comprobante y su operación en una sola transacción. Un fallo revierte ambos; repetir la ejecución devuelve el mismo resultado. Las validaciones, versiones y permisos siguen en el servidor. No existe aprobación del modelo ni guardado comercial automático al adjuntar. Conversación y resultado se recuperan al recargar; «Cancelar» descarta el contexto del soporte y la propuesta sin ejecutar, limpia la conversación e impide que una respuesta tardía la reactive. Está disponible durante el procesamiento. «Otro comprobante» también descarta el contexto anterior. Los registros ya guardados y la evidencia original de auditoría se conservan; volver a adjuntar el mismo archivo inicia una conversación limpia, sin repetir una extracción ya disponible.

La nueva experiencia se verificó con mocks en una base aislada, sin nuevas llamadas reales a OpenAI. La evidencia previa de OCR/agente reales corresponde al recorrido anterior.

## Configurar IA

```bash
mkdir -p backend
cp backend/.env.example backend/.env
```

Escribe la clave únicamente en `backend/.env`:

```dotenv
OPENAI_API_KEY=tu_clave_privada
OPENAI_OCR_MODEL=gpt-5.6-luna
OPENAI_CHAT_MODEL=gpt-5.6-luna
```

Ambos modelos fueron elegidos explícitamente. El OCR rechaza sustituciones automáticas. La aplicación no lee `.env` de la raíz. No pegues claves en el chat, frontend o Git. La extracción con ese modelo funcionó en la cuenta usada para la prueba del 054. Su resultado no sustituye la revisión humana ni valida todos los escenarios. Un error de API se muestra sin fabricar una extracción ni un registro comercial.

Sin clave puedes consultar ventas, catálogo, chat de comandos y los registros que ya existan. La IA solo se invoca al reconocer un soporte o enviar un mensaje con «Usar agente con IA» activado. No hay procesamiento automático en masa. Las imágenes se envían a OpenAI únicamente para la extracción solicitada; no se visitan enlaces ni QR.

## Recorrido completo

1. En **Mesa de trabajo** (`/mesa`), carga PNG/JPEG o elige uno de los 12 ejemplos. El archivo persiste; una carga idéntica conserva su ID.
2. Pulsa **Reconocer soporte con IA**. La lectura validada queda conservada con modelo, fecha, procedencia y hash del prompt.
3. En **Registros y propuestas**, revisa los campos contra el original visible. Corrige lo necesario y escribe una constancia de revisión. La extracción original permanece inmutable; las correcciones tienen procedencia humana.
4. Prepara el registro, revisa la propuesta, marca la aprobación y pulsa **Aprobar esta versión**. Después pulsa **Ejecutar versión aprobada**. Puedes volver a consultar el comprobante por ID.
5. Desde el comprobante busca ventas. Si hay varios candidatos, selecciona expresamente con el comerciante. Un monto igual no prueba una relación.
6. Prepara la asociación indicando importe aplicado y confirmando moneda y ausencia de duplicidad. Si falta la venta, el comerciante debe confirmarlo y aportar fecha comercial, productos, cantidades y precios. Consulta y agrega productos del catálogo. Los datos incompletos pueden quedar como borrador.
7. Revisa, aprueba y ejecuta la propuesta comercial. Una nueva venta, sus líneas, operación y vínculo se guardan juntos en una transacción. La repetición devuelve el mismo resultado. Una edición incrementa la versión e invalida la aprobación anterior.
8. Si es otra fotografía de la misma operación, usa **Proponer adjuntar a operación existente**: añade evidencia sin duplicar dinero.

El agente puede buscar ventas, consultar catálogo, consultar registros y preparar propuestas. Pide datos faltantes; no tiene herramientas de aprobación, ejecución, SQL ni acceso libre al disco. Tiene límites de seis pasos/herramientas y 90 segundos por turno. Los comandos `ayuda`, `ventas`, `ventas 134200` y `venta V-001` siguen disponibles en el chat determinista. El historial conserva el origen de cada mensaje.

## Límites comerciales

- Catálogo y precios son la fuente comercial; el inventario es solo lectura.
- No se registran compras ni se descuentan existencias.
- No hay verificación bancaria: las operaciones permanecen `no_verificado`.
- Financiación y cobro se distinguen. El efectivo mencionado no se suma al soporte.
- Se admite una operación a una venta, varios abonos por venta y varios soportes para una operación.
- Referencias son texto; ausencias son null. No se infieren cliente, factura o líneas desde un pago.
- Si hay fracciones de peso se conserva la extracción y se bloquea el registro comercial, sin redondear.
- Gastos y documentos sin clasificar se pueden revisar, pero no usar como ingreso.
- Un hash detecta archivos idénticos. Referencias coincidentes bloquean otra operación; una segunda fotografía sin referencia requiere comparación y confirmación humana.
- App para un operador en localhost. No incluye autenticación multiusuario ni despliegue público.

## Datos y archivos

SQLite contiene 75 proveedores sin contactos, 1.250 productos, 827 filas de inventario y ocho ventas ficticias. La semilla es independiente: no se lee ni modifica el proyecto o los materiales del módulo 3. Las líneas comerciales son ficticias y no se extrajeron de las imágenes.

`docente/` conserva escenarios inventados para enseñanza. La aplicación y las pruebas de OCR no lo utilizan como respuesta del modelo.

```text
src/app.py              servidor, API local y protección de escrituras
src/ia.py               cliente Responses API y configuración privada
src/ejercicios.py       extracción, revisión, propuestas y transacciones
src/agente.py           bucle de herramientas permitidas
src/chat.py             chat de comandos determinista
src/migraciones.py      migraciones v1 → v2 → v3 → v4 → v5, sin reemplazar datos
src/asistente.py        sesiones del bot flotante y recuperación
static/home.*          diseño y comportamiento de la home
src/db.py               semilla y consultas SQLite
templates/ + static/    interfaz sin compilación
backend/.env.example   plantilla privada, sin clave
prompts/                prompt original íntegro y esquema v1
soportes/               12 imágenes autorizadas
datos/practica/         base e imágenes del operador (fuera de Git)
```

## Pruebas y evidencia

```bash
uv run pytest -q
```

Se verifican infraestructura, revisión, aprobación por versión, idempotencia concurrente, transacciones, pagos parciales, financiación, duplicidad de referencias, adjuntar evidencia, migraciones, límites del agente y ZIP limpio. Las pruebas con API simulada están identificadas y usan bases temporales. Consulta [VALIDACION](docs/VALIDACION.md) para separar evidencia real de mocks y [CONTRATOS](docs/CONTRATOS.md) para la API.

## Recuperar y entregar

Detén la app y ejecuta `uv run python -m scripts.reiniciar` para reiniciar con confirmación `REINICIAR`. Guarda respaldo de toda la práctica, incluidas imágenes y registros nuevos. Para recuperar, restaura la carpeta completa con la app detenida.

```bash
uv run python -m scripts.empaquetar
```

Genera un ZIP en la carpeta superior con una SQLite nueva y migrada, los 12 ejemplos verificados y la plantilla de configuración sin clave. Excluye estado personal, claves, respaldos, entornos y cachés. La copia docente sigue separada.

Si el puerto 8008 está ocupado, usa `uv run flask --app src.app:crear_app run --host 127.0.0.1 --port 8009`. Si una escritura pide recargar, recarga para obtener el token del nuevo inicio. Un error de conexión tras ejecutar se resuelve consultando la propuesta por ID antes de reintentar.
