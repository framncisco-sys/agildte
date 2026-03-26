"""
Constantes DTE / MH El Salvador (códigos de tipo de documento).
Usado en documentoRelacionado.tipoDocumento y correlativos.
"""
# tipo_venta (modelo Venta) → código de 2 dígitos del catálogo MH (identificación.tipoDte / documento relacionado)
TIPO_VENTA_A_CODIGO_DOCUMENTO_MH = {
    'CF': '01',
    'CCF': '03',
    'NC': '05',
    'ND': '06',
    'FSE': '14',
}


def codigo_documento_mh_por_tipo_venta(tipo_venta: str, default: str = '03') -> str:
    if not tipo_venta:
        return default
    return TIPO_VENTA_A_CODIGO_DOCUMENTO_MH.get(str(tipo_venta).strip().upper(), default)
