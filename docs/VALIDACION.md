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
