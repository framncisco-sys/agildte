"""
Director / Factory para generación de DTE según tipo de venta o tipo de documento.
Patrón Strategy: selecciona el builder correcto (DTE-01, 03, 05, 06, 07, 08, 09, 14, 15).
"""
from api.models import Venta
from .dte_01_builder import DTE01Builder
from .dte_03_builder import DTE03Builder
from .dte_05_builder import DTE05Builder
from .dte_06_builder import DTE06Builder
from .dte_07_builder import DTE07Builder
from .dte_08_builder import DTE08Builder
from .dte_09_builder import DTE09Builder
from .dte_14_builder import DTE14Builder
from .dte_15_builder import DTE15Builder


def get_builder(tipo_dte: str, documento=None, empresa=None):
    """
    Devuelve la instancia del builder apropiado según tipo_dte.

    Para DTE 01, 03, 05, 06: documento debe ser Venta, empresa se obtiene de venta.empresa.
    Para DTE 07, 08, 09, 14, 15: documento y empresa son requeridos (documento puede ser RetencionRecibida, Liquidacion, Compra, dict).

    Args:
        tipo_dte: '01', '03', '05', '06', '07', '08', '09', '14', '15'
        documento: Venta (para 01/03/05/06) o documento específico (para 07-15)
        empresa: Empresa (requerido para 07-15, opcional para 01-06 si documento es Venta)

    Returns:
        Instancia del builder configurada
    """
    tipo = str(tipo_dte).strip().zfill(2)
    if tipo == '01':
        return DTE01Builder(documento)
    if tipo == '03':
        return DTE03Builder(documento)
    if tipo == '05':
        return DTE05Builder(documento)
    if tipo == '06':
        return DTE06Builder(documento)
    if tipo == '07':
        return DTE07Builder(documento, empresa)
    if tipo == '08':
        return DTE08Builder(documento, empresa)
    if tipo == '09':
        return DTE09Builder(documento, empresa)
    if tipo == '14':
        return DTE14Builder(documento, empresa)
    if tipo == '15':
        return DTE15Builder(documento, empresa)
    raise ValueError(f"Tipo DTE no soportado: {tipo_dte}")


def generar_dte(venta: Venta, ambiente: str = '00', tipo_dte_override: str = None, **kwargs) -> dict:
    """
    Genera el JSON del DTE según el tipo de venta.

    Args:
        venta: Instancia de Venta
        ambiente: '00' = Pruebas, '01' = Producción
        tipo_dte_override: Si se especifica ('05', '06'), fuerza ese tipo (para NC/ND)
        **kwargs: Parámetros adicionales para generar_json (generar_codigo, generar_numero_control)

    Returns:
        dict: JSON del DTE listo para firma y envío a MH

    Raises:
        ValueError: Si el tipo de venta no es soportado
    """
    if not isinstance(venta, Venta):
        raise ValueError("Se requiere una instancia de Venta")

    tipo = tipo_dte_override or getattr(venta, 'tipo_dte', None) or getattr(venta, 'tipo_venta', None) or 'CF'

    # Mapeo tipo_venta / tipo_dte -> builder
    _map = {'CF': '01', 'CCF': '03', 'NC': '05', 'ND': '06', '01': '01', '03': '03', '05': '05', '06': '06'}
    tipo_str = str(tipo).upper()
    tipo_num = _map.get(tipo_str, tipo_str)
    if tipo_num not in ('01', '03', '05', '06'):
        raise ValueError(f"Tipo de venta no soportado para generar_dte: {tipo}. Use CF, CCF, NC o ND.")

    builder = get_builder(tipo_num, venta, venta.empresa)
    return builder.generar_json(ambiente=ambiente, **kwargs)


def generar_dte_documento(documento, empresa, tipo_dte: str, ambiente: str = '00', **kwargs) -> dict:
    """
    Genera el JSON del DTE para documentos que no son Venta (Retención, Liquidación, Compra, Donación).

    Args:
        documento: RetencionRecibida, Liquidacion, Compra, o dict con la estructura requerida
        empresa: Instancia de Empresa
        tipo_dte: '07', '08', '09', '14', '15'
        ambiente: '00' = Pruebas, '01' = Producción
        **kwargs: generar_codigo, generar_numero_control

    Returns:
        dict: JSON del DTE listo para firma y envío a MH
    """
    builder = get_builder(str(tipo_dte).strip().zfill(2), documento, empresa)
    return builder.generar_json(ambiente=ambiente, **kwargs)
