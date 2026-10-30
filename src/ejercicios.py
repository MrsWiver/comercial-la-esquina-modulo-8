"""Puntos de extensión. No simulan OCR ni escriben ventas como si estuvieran aprobadas.

El taller implementa cada función y sus validaciones siguiendo docs/CONTRATOS.md.
Las rutas devuelven 501 mientras estas funciones estén pendientes.
"""
OCR_MODEL = 'gpt-5.6-luna'


def extraer_soporte(archivo, db):
    # Ejercicio 1: backend, prompt íntegro, esquema y validación semántica.
    raise NotImplementedError('Ejercicio 1: falta conectar y validar el reconocimiento del soporte.')


def registrar_comprobante(datos, db):
    # Ejercicio 1: revisión humana, persistencia y consulta por ID.
    raise NotImplementedError('Ejercicio 1: falta registrar el comprobante revisado.')


def preparar_operacion(datos, db):
    # Ejercicio 2/3: propuesta exacta, versionada y pendiente de aprobación humana.
    raise NotImplementedError('Ejercicios 2 y 3: falta preparar la propuesta comercial.')


def registrar_operacion_aprobada(datos, db):
    # Ejercicio 2/3: validar aprobación en servidor y ejecutar una sola vez.
    raise NotImplementedError('Ejercicios 2 y 3: falta ejecutar la propuesta aprobada.')
