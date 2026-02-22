"""
Clase base para generación de DTE (Documento Tributario Electrónico).
Implementa lógica común según estándar MH El Salvador.
"""
import uuid
import copy
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP

# Zona horaria de El Salvador (UTC-6) para fecEmi/horEmi
TZ_EL_SALVADOR = timezone(timedelta(hours=-6))

from api.models import Venta
from api.dte_generator import CorrelativoDTE, formatear_decimal, limpiar_nulos


def _es_valor_vacio(valor):
    """True si el valor debe omitirse (None, "", o string solo espacios)."""
    if valor is None:
        return True
    if isinstance(valor, str) and (not valor or not valor.strip()):
        return True
    return False


def _complemento_receptor(valor):
    """Complemento de dirección para receptor."""
    return valor if valor and str(valor).strip() else "San Miguel"


class BaseDTEBuilder(ABC):
    """Clase base abstracta para builders de DTE."""

    TIPO_DTE = None  # '01' o '03'
    VERSION_DTE = None  # 1 o 3

    def __init__(self, venta: Venta):
        if not isinstance(venta, Venta):
            raise ValueError("Se requiere una instancia de Venta")
        self.venta = venta
        self.empresa = venta.empresa

    def _limpiar_texto(self, valor):
        """Limpia texto: strip, retorna None si vacío."""
        if valor is None:
            return None
        s = str(valor).strip()
        return s if s else None

    def _obtener_codigos_establecimiento(self):
        """Obtiene cod_estable y cod_punto_venta desde empresa."""
        cod_estable = self.empresa.cod_establecimiento or 'M001'
        cod_estable = cod_estable.strip() if cod_estable and cod_estable.strip() else 'M001'
        cod_punto_venta = self.empresa.cod_punto_venta or 'P001'
        cod_punto_venta = cod_punto_venta.strip() if cod_punto_venta and cod_punto_venta.strip() else 'P001'
        return cod_estable, cod_punto_venta

    def _construir_emisor(self):
        """Construye la sección emisor con campos V3 (codEstableMH, codEstable, codPuntoVentaMH, codPuntoVenta)."""
        if not self.empresa:
            raise ValueError("La venta debe tener una empresa asociada")

        cod_actividad = self.empresa.cod_actividad or "62010"
        desc_actividad = self.empresa.desc_actividad or "Desarrollo de software"
        codigo_departamento = str(self.empresa.departamento or "06").strip().zfill(2)
        codigo_municipio = str(self.empresa.municipio or "14").strip().zfill(2)
        nit_limpio = (self.empresa.nit or self.empresa.nrc or "").replace('-', '').replace(' ', '')
        cod_estable, cod_punto_venta = self._obtener_codigos_establecimiento()

        emisor = {
            "nit": nit_limpio,
            "nrc": self.empresa.nrc,
            "nombre": self.empresa.nombre,
            "codActividad": cod_actividad,
            "descActividad": desc_actividad,
            "tipoEstablecimiento": "01",
            "direccion": {
                "departamento": codigo_departamento,
                "municipio": codigo_municipio,
                "complemento": (self.empresa.direccion or "").strip()
            },
            "codEstableMH": cod_estable,
            "codEstable": cod_estable,
            "codPuntoVentaMH": cod_punto_venta,
            "codPuntoVenta": cod_punto_venta,
            "nombreComercial": (
                (getattr(self.empresa, 'nombre_comercial', None) or "").strip()
                or (self.empresa.nombre or "Empresa").strip()
                or "Empresa"
            ),
        }
        if self.empresa.telefono:
            emisor["telefono"] = self.empresa.telefono
        if self.empresa.correo:
            emisor["correo"] = self.empresa.correo
        return emisor

    def _generar_identificacion(self, ambiente, fecha_str, hora_actual):
        """Genera la sección identificación del DTE."""
        cod_estable, cod_punto_venta = self._obtener_codigos_establecimiento()
        numero_control = self.venta.numero_control or ""

        if not numero_control or len(numero_control) != 31:
            self.venta.numero_control = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=self.empresa.id if self.empresa else None,
                tipo_dte=self.TIPO_DTE,
                sucursal=cod_estable,
                punto=cod_punto_venta
            )
            numero_control = self.venta.numero_control

        codigo_generacion = self.venta.codigo_generacion or str(uuid.uuid4())
        codigo_generacion = codigo_generacion.upper()

        # tipoContingencia y motivoContin deben ser null al transmitir a MH (operación normal)
        return {
            "version": self.VERSION_DTE,
            "ambiente": ambiente,
            "tipoDte": self.TIPO_DTE,
            "numeroControl": numero_control,
            "codigoGeneracion": codigo_generacion,
            "fecEmi": fecha_str,
            "horEmi": hora_actual,
            "tipoModelo": 1,
            "tipoOperacion": 1,
            "tipoContingencia": None,
            "motivoContin": None,
            "tipoMoneda": "USD",
        }

    def _generar_extension(self):
        """Extension con campos requeridos por MH (pueden ser null)."""
        ext = {
            "nombEntrega": None,
            "docuEntrega": None,
            "nombRecibe": None,
            "docuRecibe": None,
            "observaciones": None,
            "placaVehiculo": None,
        }
        for key, attr in [
            ("docuEntrega", "docu_entrega"),
            ("docuRecibe", "docu_recibe"),
            ("placaVehiculo", "placa_vehiculo"),
            ("observaciones", "observaciones"),
            ("nombEntrega", "nomb_entrega"),
            ("nombRecibe", "nomb_recibe"),
        ]:
            val = getattr(self.venta, attr, None)
            if val:
                ext[key] = val
        return ext

    def _numero_a_letras(self, numero):
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

    def _campos_requeridos_mh(self):
        """Campos que MH exige presentes (pueden ser null o lista vacía)."""
        return [
            "identificacion.tipoContingencia", "identificacion.motivoContin",
            "documentoRelacionado", "otrosDocumentos", "ventaTercero", "extension", "apendice",
            "extension.nombEntrega", "extension.docuEntrega", "extension.nombRecibe",
            "extension.docuRecibe", "extension.observaciones", "extension.placaVehiculo",
            "emisor.codEstableMH", "emisor.codEstable", "emisor.codPuntoVentaMH", "emisor.codPuntoVenta",
            "emisor.nombreComercial",
            "resumen.numPagoElectronico", "resumen.ivaRete1",
            "resumen.pagos.referencia", "resumen.pagos.periodo", "resumen.pagos.plazo",
            "cuerpoDocumento.numeroDocumento", "cuerpoDocumento.codTributo",
            # tributos:[] debe preservarse (MH exige [] en ítems exentos de CCF/NC/ND)
            "cuerpoDocumento.tributos",
        ]

    def _limpiar_diccionario_dte(self, dte_json):
        """Limpia el diccionario DTE según esquema MH."""
        dte_limpio = copy.deepcopy(dte_json)
        dte_limpio = limpiar_nulos(dte_limpio, campos_requeridos=self._campos_requeridos_mh())
        if "resumen" in dte_limpio and isinstance(dte_limpio["resumen"], dict):
            resumen = dte_limpio["resumen"]
            if "reteIVA" in resumen and resumen["reteIVA"] in (0, 0.0):
                del resumen["reteIVA"]
        return dte_limpio

    @abstractmethod
    def _construir_receptor(self):
        """Construye la sección receptor. Específico por tipo DTE."""
        pass

    @abstractmethod
    def _construir_cuerpo_documento(self):
        """Construye cuerpoDocumento. Específico por tipo DTE."""
        pass

    @abstractmethod
    def _construir_resumen(self, cuerpo_documento):
        """Construye resumen. Específico por tipo DTE."""
        pass

    def generar_json(self, ambiente='00', generar_codigo=True, generar_numero_control=True):
        """Genera el JSON completo del DTE."""
        if generar_codigo and not self.venta.codigo_generacion:
            self.venta.codigo_generacion = str(uuid.uuid4()).upper()

        ahora_sv = datetime.now(TZ_EL_SALVADOR)
        hora_actual = ahora_sv.strftime('%H:%M:%S')
        # fecEmi SIEMPRE es la fecha actual: MH exige que coincida con la fecha de envío.
        # Para NC/ND la venta puede tener fecha_emision del documento original, pero el DTE
        # que se genera y envía AHORA debe llevar la fecha de hoy.
        fecha_str = ahora_sv.strftime('%Y-%m-%d')

        cuerpo_documento = self._construir_cuerpo_documento()
        dte_json = {
            "identificacion": self._generar_identificacion(ambiente, fecha_str, hora_actual),
            "documentoRelacionado": None,
            "emisor": self._construir_emisor(),
            "receptor": self._construir_receptor(),
            "otrosDocumentos": None,
            "ventaTercero": None,
            "cuerpoDocumento": cuerpo_documento,
            "resumen": self._construir_resumen(cuerpo_documento),
            "extension": self._generar_extension(),
            "apendice": None,
        }
        return self._limpiar_diccionario_dte(dte_json)
