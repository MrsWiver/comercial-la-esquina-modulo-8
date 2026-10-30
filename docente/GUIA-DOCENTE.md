# Guía docente · respuestas y datos del comerciante

Esta guía acompaña la base estudiantil; no es una solución programada. La app nunca la lee. Retírala si deseas entregar los casos sin respuestas.

Los datos observados se leyeron manualmente de las 12 imágenes. No se ejecutó OCR ni se verificó autenticidad o abono bancario. Los IDs, clientes, productos, cantidades y fechas comerciales son escenarios ficticios creados para el taller.

## Mapa de casos

| Archivo | Valor visible COP | Tipo | Recorrido comercial ficticio |
| --- | ---: | --- | --- |
| comprobante_001.png | 130700 | sistecredito_credit | Confirmar con el comerciante y asociar a V-001 |
| comprobante_002.png | 158100 | sistecredito_credit | Falta venta: pedir detalle comercial y crear tras aprobación. |
| comprobante_013.png | 22000 | card_voucher | Confirmar con el comerciante y asociar a V-002 |
| comprobante_022.png | 134200 | card_voucher | Dos candidatos V-003 y V-004. El comerciante confirma V-004 cuando se le pregunta. |
| comprobante_026.png | 30000 | card_voucher | Falta venta: pedir detalle comercial y crear tras aprobación. |
| comprobante_037.png | 400000 | addi_credit | Confirmar con el comerciante y asociar a V-005 |
| comprobante_039.png | 118700 | addi_credit | Falta venta: pedir detalle comercial y crear tras aprobación. |
| comprobante_041.png | 19400 | transfer | V-006 total 100000: abono 19400. La mención de efectivo 50000 no acredita otro pago. |
| comprobante_050.png | 172100 | transfer | Confirmar con el comerciante y asociar a V-007 |
| comprobante_052.png | 280000 | transfer | Falta venta: pedir detalle comercial y crear tras aprobación. |
| comprobante_054.png | 148000 | transfer | Falta venta: pedir detalle comercial y crear tras aprobación. |
| comprobante_060.png | 76800 | transfer | V-008 del 17 de septiembre; pago del 18. No exigir igualdad de fecha. |

## Qué responder cuando el alumno pida datos

Entregar las líneas siguientes solo cuando la persona confirme que falta la venta y solicite productos, cantidades, precios y fecha comercial. Los precios son los del catálogo de origen, incluso si no representan precios habituales de mercado. El catálogo no se ajustó para hacer coincidir montos.

Para los casos existentes, confirmar el ID desde el registro comercial ficticio de la tienda. Los nombres de beneficiarios particulares no identifican al comprador ni a Comercial La Esquina. El monto y la fecha no bastan para demostrar coincidencia. No hay referencias de factura legibles en estos 12 ejemplos.

### comprobante_002.png

Comerciante: «Sí, falta registrar esta venta. Fecha comercial 2026-05-13. Cliente: Comprador práctica 002 (ficticio). No tengo una referencia externa de factura para informar.»

- 1 × FER-0001 · Martillo de uña Forte Mini · 121300 COP por unidad.
- 1 × FER-0094 · Tornillo galvanizado Roble Grande · 36800 COP por unidad.

Total calculado: **158100 COP**. Es financiación, sin acreditar efectivo recibido.

### comprobante_026.png

Comerciante: «Sí, falta registrar esta venta. Fecha comercial 2026-09-18. Cliente: Comprador práctica 026 (ficticio). No tengo una referencia externa de factura para informar.»

- 1 × MIS-0234 · Kit de costura Nova Grande · 30000 COP por unidad.

Total calculado: **30000 COP**. En este escenario cubre el total; la recepción bancaria sigue sin verificar.

### comprobante_039.png

Comerciante: «Sí, falta registrar esta venta. Fecha comercial 2026-09-07. Cliente: Comprador práctica 039 (ficticio). No tengo una referencia externa de factura para informar.»

- 1 × FER-0099 · Tornillo galvanizado Roble Reforzado · 118700 COP por unidad.

Total calculado: **118700 COP**. Es financiación, sin acreditar efectivo recibido.

### comprobante_052.png

Comerciante: «Sí, falta registrar esta venta. Fecha comercial 2026-09-08. Cliente: Comprador práctica 052 (ficticio). No tengo una referencia externa de factura para informar.»

- 1 × FER-0012 · Destornillador plano Andino Pequeño · 91600 COP por unidad.
- 1 × FER-0127 · Candado de seguridad Andino Clásico · 188400 COP por unidad.

Total calculado: **280000 COP**. En este escenario cubre el total; la recepción bancaria sigue sin verificar.

### comprobante_054.png

Comerciante: «Sí, falta registrar esta venta. Fecha comercial 2026-09-11. Cliente: Comprador práctica 054 (ficticio). No tengo una referencia externa de factura para informar.»

- 1 × FER-0001 · Martillo de uña Forte Mini · 121300 COP por unidad.
- 1 × FER-0222 · Cinta aislante Andino Pequeño · 26700 COP por unidad.

Total calculado: **148000 COP**. En este escenario cubre el total; la recepción bancaria sigue sin verificar.

## Lecturas y cuidados

- 054: DaviPlata, 148000, 2026-09-11, 12:14:00 con precisión de minuto; merchant_or_store=null, notes=null. Referencias ocultas en null.
- 022: Visa crédito. El «3» de VISA 3 no son cuotas ni tipo de tarjeta. Fecha 9/23/2026 = 23 de septiembre.
- 001 y 002: valor del crédito Sistecrédito; no sumar cuotas e intereses. Fechas DD/MM/YYYY.
- 037 y 039: valor financiado Addi; no confundir al usuario del portal con comercio o cliente de la venta.
- 013 y 026: no se lee marca/tipo de tarjeta, mantener medio en null. Credibanco es procesador, no marca de tarjeta.
- 041: envío 19400; stated_cash_amount=50000; notes conserva solo «efectivo osea 50000». No sumar ni acreditar el efectivo mencionado.
- Los segundos no están visibles en estos ejemplos: usar time_precision=minute y documentar normalización a 00. Si no hay hora visible, null.
- Todos los identificadores de referencias de estos ejemplos están ocultos. No rellenarlos por formato ni por valores de la semilla.

El JSON casos-revisados.json conserva valores esperados parciales por campo y hashes originales. No es una respuesta completa conforme al esquema de la API: no inventa confianza ni evidencia textual adicional. Para evaluar un modelo, comparar únicamente lo revisado y completar el patrón esperado mediante nueva revisión humana.

## Cobertura pendiente

Estos ejemplos no incluyen una factura de transporte, total oculto, factura externa legible, texto malicioso ni otra foto del mismo soporte. Crear fixtures sintéticos marcados y expectativas revisadas antes de declarar esos casos cubiertos. La doble aprobación, las propuestas modificadas y la recuperación de vínculos requieren implementar los ejercicios y sus pruebas.
