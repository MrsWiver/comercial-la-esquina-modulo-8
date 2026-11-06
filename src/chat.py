"""Chat de práctica determinista. No es un agente ni usa un modelo de lenguaje."""
import re
from .db import buscar_ventas


def responder(texto, db):
    t = texto.strip()
    if t.lower() in ('ayuda','hola','/ayuda'):
        return ('Soy el chat de práctica, sin IA conectada. Puedo consultar SQLite con estos comandos:\n'
                '• ventas\n• ventas 148000 (importe entero en COP)\n• venta V-001\n'
                'La carga de imágenes ya funciona. Usa Reconocer soporte y Registros para revisar y proponer operaciones.')
    if t.lower() == 'ventas' or re.fullmatch(r'ventas\s+\d{1,10}',t,re.I):
        partes=t.split()
        importe=int(partes[1]) if len(partes)>1 else None
        filas=buscar_ventas(db,importe=importe)
        if not filas:
            return 'No encontré ventas con ese importe. Amplía la búsqueda en Ventas: un abono o una fecha distinta puede requerir otros criterios.'
        listado='\n'.join(f"{v['id']} · {v['fecha_comercial']} · ${format(v['total'], ',').replace(',', '.')} COP · {v['cliente']}" for v in filas)
        return listado+'\nEstos son candidatos de consulta. El importe por sí solo no demuestra una relación con un soporte.'
    if re.fullmatch(r'venta\s+V-(?:\d{3}|[a-f0-9]{16})',t,re.I):
        ident=t.split()[1]
        ident='V-'+ident[2:]
        filas=buscar_ventas(db,texto=ident)
        if filas:
            v=filas[0]
            return f"{v['id']} · {v['cliente']} · {v['fecha_comercial']} · ${format(v['total'], ',').replace(',', '.')} COP. Abre su detalle en Ventas para consultar las líneas. Consulta los vínculos comerciales en el detalle; no verifica recepción bancaria."
        return 'Ese ID no existe. Puedes consultar los IDs en Ventas.'
    return ('Este chat inicial entiende comandos de consulta, no lenguaje libre. Escribe «ayuda» para verlos. '
            'Activa «Usar agente con IA» para conversar con herramientas; requiere una clave configurada.')
