# Comercial La Esquina · Proyecto inicial del módulo 8

Una app local para comenzar a construir el agente de comprobantes. Incluye chat de práctica, imágenes, consultas y SQLite. **Todavía no reconoce comprobantes ni registra pagos o nuevas ventas. Esas son las actividades del taller.**

## Empezar en tres pasos

Necesitas [uv](https://docs.astral.sh/uv/getting-started/installation/) y Python 3.11 o superior. Si no tienes Python, `uv python install 3.14` lo instala. Puedes [descargar el proyecto listo en ZIP](https://github.com/MrsWiver/comercial-la-esquina-modulo-8/releases/latest) o clonarlo:

```bash
git clone https://github.com/MrsWiver/comercial-la-esquina-modulo-8.git
cd comercial-la-esquina-modulo-8
```

Abre una terminal en la carpeta del proyecto, donde está este README.

```bash
uv sync --locked
uv run python -m scripts.iniciar_datos
uv run python -m src.app
```

Abre **http://127.0.0.1:8008** en tu navegador. Mantén la terminal abierta. Para detener, presiona `Ctrl+C`. La app se ejecuta solo en tu equipo; no necesita cuentas ni clave de API en esta etapa. La primera instalación sí descarga las dependencias.

El ZIP de la entrega trae `datos/practica/negocio.sqlite3` ya creada y limpia. Al clonar, esa base se crea desde la semilla con el comando anterior o al iniciar. La base de trabajo se excluye de Git para conservar separados los datos de cada estudiante. Nunca se reemplaza una base existente automáticamente.

## Qué puedes hacer desde el inicio

- **Mesa de trabajo:** cargar PNG/JPEG, ver la imagen, ampliarla y recuperar los archivos guardados. El mismo archivo conserva un solo ID aunque se cargue dos veces.
- **Chat de práctica:** escribir `ayuda`, `ventas`, `ventas 134200` o `venta V-001`. Consulta la base y conserva la conversación. Es determinista y está identificado como chat sin IA.
- **Ventas:** buscar por ID, cliente, total exacto o fecha comercial. Abrir las líneas y su total calculado.
- **Catálogo:** consultar los 1.250 productos con precios del módulo 3.
- **Soportes de práctica:** explorar las 12 imágenes anonimizadas y cargar una al espacio de trabajo.

Un archivo cargado **no es un comprobante revisado ni un pago registrado**. La app no descuenta inventario, no verifica movimientos bancarios y no llama a servicios externos.

## Qué construirás en clase

1. Reconocer la imagen con el prompt y esquema incluidos, revisar los datos y registrar el comprobante.
2. Buscar ventas, preparar una asociación y guardarla después de una confirmación explícita.
3. Completar una venta faltante con productos y cantidades confirmados, calcular su total y crearla con su relación al soporte.

Las funciones por completar están en `src/ejercicios.py`. Sus rutas ya existen y responden HTTP 501, «pendiente del taller». No devuelven éxitos simulados. La ficha editable, las propuestas, sus aprobaciones, los registros comerciales y sus vistas de consulta forman parte de las actividades. Consulta [el taller por etapas](docs/TALLER.md) y [los contratos](docs/CONTRATOS.md).

## Datos de la práctica

El SQLite contiene **75 proveedores, 1.250 productos, 827 filas de inventario y 8 ventas ficticias nuevas**. Catálogo, precios e inventario proceden de una instantánea del módulo 3; se excluyeron contactos, teléfonos, correos y NIT de proveedores. El proyecto y Excel originales no se modificaron.

Siete soportes tienen escenarios con ventas existentes; uno de ellos tiene dos candidatos del mismo valor. Cinco soportes quedan sin venta. También hay un pago parcial y una fecha de pago distinta de la venta. Todos comienzan sin pagos asociados ni comprobantes registrados.

Las líneas comerciales son **ficticias** y usan códigos y precios del catálogo. No son productos extraídos de los soportes. No se inventaron referencias de factura en las imágenes; sus identificadores están ocultos. Las imágenes conservan la anonimización aportada por el usuario. [Procedencia](datos/semilla/procedencia.json).

La carpeta `docente/` contiene respuestas y datos para representar al comerciante durante la clase. Se puede retirar antes de distribuir al alumnado: la app no la utiliza. No hay una solución docente completa implementada.

## Configuración privada para el ejercicio de IA

Cuando implementes el cliente de reconocimiento en el backend:

1. Copia `.env.example` a `.env`.
2. Escribe tu clave en `OPENAI_API_KEY`.
3. Conserva **`OPENAI_OCR_MODEL=gpt-5.6-luna`**.
4. Implementa la lectura de `.env` en el backend y el cliente de API como indica el taller.

La base inicial **no lee `.env` ni envía imágenes a una API**. Cambiar esa configuración todavía no activa el reconocimiento. No pegues la clave en el chat, HTML, capturas o Git. El modelo conversacional se elige por separado al implementar el agente. El prompt original está íntegro en `prompts/extractor-v1.txt`.

## Reiniciar o recuperar la práctica

Cerrar la app y volver a abrirla conserva base, chat e imágenes. Para volver a las ocho ventas iniciales:

1. Detén la app con `Ctrl+C`.
2. Ejecuta `uv run python -m scripts.reiniciar`.
3. Escribe `REINICIAR` cuando se solicite.
4. Inicia de nuevo la app.

El script guarda **toda la carpeta de práctica**, incluida la base y las imágenes, en `datos/respaldos/` con fecha UTC. Para recuperar un respaldo, detén la app, mueve la práctica actual a otra carpeta y copia el contenido completo del respaldo a `datos/practica/`. No recuperes únicamente SQLite si quieres conservar la evidencia visual.

## Pruebas

```bash
uv run pytest -q
```

Prueban la semilla, consultas exactas, ambigüedad, carga válida e inválida, tamaño, duplicados concurrentes, persistencia, protección de escrituras, fallas de disco y funciones pendientes. No son pruebas reales del modelo ni de los ejercicios sin implementar. [Evidencia y límites](docs/VALIDACION.md).

## Si algo falla

| Síntoma | Qué hacer |
| --- | --- |
| `uv` no se reconoce | Instala uv desde su documentación oficial y abre una terminal nueva. |
| `No module named src` | Abre la terminal en la carpeta que contiene este README. Ejecuta los comandos con `-m`. |
| Puerto 8008 ocupado | Cierra la otra instancia o ejecuta `uv run flask --app src.app:crear_app run --host 127.0.0.1 --port 8009`. Abre ese mismo puerto en el navegador. |
| «Recarga la aplicación» | Recarga la pestaña: cada inicio genera un token nuevo para las escrituras locales. |
| La carga falla | Usa una imagen PNG/JPEG válida, hasta 8 MB y 24 millones de píxeles. Un PDF o una extensión cambiada no basta. |
| «Falta el original» | Recupera la carpeta de práctica completa desde un respaldo. No se declara que la evidencia esté disponible si falta el archivo. |
| Chat no entiende una frase | Escribe `ayuda`. El agente conversacional todavía se construye en clase. |
| «Pendiente del taller» | Es una función por implementar; no se arregla agregando una clave. |

Usa una sola instancia por carpeta de datos. Al iniciar se recuperan temporales y archivos huérfanos de cargas interrumpidas. Este servidor está preparado para una práctica local de un operador. Publicar una app requiere una etapa diferente.

## Estructura

```text
src/app.py              servidor y rutas
src/db.py               creación y consultas SQLite
src/chat.py             chat de comandos de práctica
src/ejercicios.py       funciones para construir en clase
templates/ + static/    interfaz sin proceso de compilación
datos/esquema.sql       tablas y vista de totales
datos/semilla/          instantánea portable y ventas ficticias
datos/practica/         SQLite e imágenes de cada estudiante
soportes/               12 imágenes de ejemplo
prompts/                prompt íntegro y esquema de extracción v1
docs/                   recorrido y contratos del taller
docente/                respuestas y datos comerciales ficticios
tests/                  pruebas automatizadas
```

Se eligió Python + Flask + HTML/CSS/JavaScript para que haya un solo servidor y no sea necesario instalar Node ni compilar el frontend. [Flask](https://flask.palletsprojects.com/en/stable/quickstart/), [Pillow](https://pillow.readthedocs.io/en/stable/reference/Image.html) y [SQLite](https://www.sqlite.org/foreignkeys.html) documentan las bases utilizadas. Las versiones están fijadas en `pyproject.toml` y `uv.lock`.

Repositorio público: [MrsWiver/comercial-la-esquina-modulo-8](https://github.com/MrsWiver/comercial-la-esquina-modulo-8). Incluye los 12 soportes de práctica anonimizados. `.env`, `datos/practica/`, respaldos y archivos personales quedan excluidos de Git. Los datos comerciales se reconstruyen desde `datos/semilla/`.

## Generar una entrega limpia

```bash
uv run python -m scripts.empaquetar
```

Crea `proyecto-inicial-modulo-8.zip` en la carpeta superior. Construye otra SQLite limpia desde la semilla, aunque tu práctica tenga imágenes o mensajes. Incluye la guía docente en una carpeta separada y los 12 ejemplos autorizados; excluye `.env`, entornos, cachés, archivos cargados y respaldos.
