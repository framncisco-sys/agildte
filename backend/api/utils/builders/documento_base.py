"""
Clase base para builders que usan documentos distintos a Venta
(Retención, Liquidación, Compra, Donación, etc.).
Proporciona helpers comunes y estructura de identificación.
"""
import uuid
import copy
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta

TZ_EL_SALVADOR = timezone(timedelta(hours=-6))

from api.dte_generator import CorrelativoDTE, formatear_decimal, limpiar_nulos


def _val(doc, attr, default=None):
    """Obtiene valor de objeto o dict."""
    if doc is None:
        return default
    if isinstance(doc, dict):
        return doc.get(attr, default)
    return getattr(doc, attr, default)


def _numero_a_letras(numero):
    """Convierte número a letras en español."""
    try:
        from num2words import num2words
        numero_entero = int(numero)
        numero_decimal = int(round((numero - numero_entero) * 100))
        texto_entero = "CERO" if numero_entero == 0 else num2words(numero_entero, lang='es', to='cardinal').upper()
        decimal_str = f"{numero_decimal:02d}"
        return f"{texto_entero} DOLARES CON {decimal_str}/100 USD"
    except (ImportError, Exception):
        try:
            numero_entero = int(numero)
            numero_decimal = int(round((numero - numero_entero) * 100))
            return f"{numero_entero} DOLARES CON {numero_decimal:02d}/100 USD"
        except Exception:
            return "CERO DOLARES CON 00/100 USD"


class BaseDocumentoDTEBuilder(ABC):
    """
    Base para builders de DTE que usan documento + empresa (no necesariamente Venta).
    documento puede ser RetencionRecibida, Liquidacion, Compra, dict, etc.
    """

    TIPO_DTE = None
    VERSION_DTE = 1

    def __init__(self, documento, empresa):
        self.documento = documento
        self.empresa = empresa

    def _obtener_codigos_establecimiento(self):
        cod_estable = _val(self.empresa, 'cod_establecimiento', None) or 'M001'
        cod_estable = str(cod_estable).strip() if cod_estable else 'M001'
        cod_punto = _val(self.empresa, 'cod_punto_venta', None) or 'P001'
        cod_punto = str(cod_punto).strip() if cod_punto else 'P001'
        return cod_estable, cod_punto

    def _generar_identificacion(self, ambiente, codigo_gen, numero_ctrl, fecha_str, hora_actual, tipo_cont=None, motivo_cont=None):
        cod_estable, cod_punto = self._obtener_codigos_establecimiento()
        if not numero_ctrl or len(str(numero_ctrl)) != 31:
            numero_ctrl = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=_val(self.empresa, 'id'),
                tipo_dte=self.TIPO_DTE,
                sucursal=cod_estable,
                punto=cod_punto
            )
        codigo_gen = (codigo_gen or str(uuid.uuid4())).upper()
        ident = {
            "version": self.VERSION_DTE,
            "ambiente": ambiente,
            "tipoDte": self.TIPO_DTE,
            "numeroControl": numero_ctrl,
            "codigoGeneracion": codigo_gen,
            "fecEmi": fecha_str,
            "horEmi": hora_actual,
            "tipoModelo": 1,
            "tipoOperacion": 1,
            "tipoMoneda": "USD",
        }
        if tipo_cont is not None:
            ident["tipoContingencia"] = tipo_cont
        if motivo_cont is not None:
            ident["motivoContin"] = motivo_cont
        return ident

    def _emisor_desde_empresa(self):
        """Emisor estándar desde empresa."""
        cod_actividad = _val(self.empresa, 'cod_actividad', None) or "62010"
        desc_actividad = _val(self.empresa, 'desc_actividad', None) or "Servicios"
        dept = str(_val(self.empresa, 'departamento', None) or "06").strip().zfill(2)
        mun = str(_val(self.empresa, 'municipio', None) or "14").strip().zfill(2)
        nit = (_val(self.empresa, 'nit', None) or _val(self.empresa, 'nrc', None) or "").replace('-', '').replace(' ', '')
        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        emisor = {
            "nit": nit,
            "nrc": _val(self.empresa, 'nrc', None),
            "nombre": _val(self.empresa, 'nombre', "Empresa"),
            "codActividad": cod_actividad,
            "descActividad": desc_actividad,
            "nombreComercial": _val(self.empresa, 'nombre_comercial', None),
            "tipoEstablecimiento": "01",
            "direccion": {"departamento": dept, "municipio": mun, "complemento": (_val(self.empresa, 'direccion', None) or "").strip()[:200] or "San Salvador"},
            "telefono": _val(self.empresa, 'telefono', None) or "22222222",
            "correo": _val(self.empresa, 'correo', None) or "info@empresa.com",
        }
        return emisor

    def _limpiar_dte(self, dte, campos_requeridos=None):
        return limpiar_nulos(copy.deepcopy(dte), campos_requeridos=campos_requeridos or [])
