"""
Builder para DTE-06 (Nota de Débito Electrónica).
Esquema fe-nd-v3. Requiere documentoRelacionado.
"""
from .dte_05_builder import DTE05Builder


class DTE06Builder(DTE05Builder):
    """Builder para Nota de Débito (DTE-06). Misma estructura que Nota Crédito."""

    TIPO_DTE = '06'
    VERSION_DTE = 3
