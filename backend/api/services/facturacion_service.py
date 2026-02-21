"""
Servicio robusto para facturación electrónica con el Ministerio de Hacienda de El Salvador.

Este servicio integra la generación de DTE, autenticación, firma digital y envío a MH.
Reemplaza el script legacy enviar_factura_final.py con una implementación orientada a objetos.
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from django.conf import settings

from ..firmador_interno import firmar_dte_interno
from ..models import Empresa, Venta
from ..utils.builders import generar_dte

logger = logging.getLogger(__name__)


class FacturacionServiceError(Exception):
    """Excepción base para errores del servicio de facturación"""
    pass


class AutenticacionMHError(FacturacionServiceError):
    """Error al autenticarse con el Ministerio de Hacienda"""
    pass


class FirmaDTEError(FacturacionServiceError):
    """Error al firmar el documento DTE"""
    pass


class EnvioMHError(FacturacionServiceError):
    """Error al enviar el DTE al Ministerio de Hacienda"""
    pass


class EnvioMHTransitorioError(EnvioMHError):
    """Error transitorio (timeout, 5xx, conexión) - factura queda PendienteEnvio para reintento"""
    pass


class FacturacionService:
    """
    Servicio para procesar facturas electrónicas con el Ministerio de Hacienda.
    
    Este servicio orquesta todo el proceso:
    1. Generación del JSON DTE usando generar_dte (Patrón Strategy)
    2. Autenticación con MH
    3. Firma digital del documento
    4. Envío a MH y procesamiento de respuesta
    
    Args:
        empresa: Instancia del modelo Empresa con credenciales configuradas
    """
    
    # URLs según empresa.ambiente:
    # '00' = PRODUCCIÓN (api.dtes.mh.gob.sv)
    # '01' = PRUEBAS   (apitest.dtes.mh.gob.sv)
    URLS_MH = {
        '00': {  # Producción
            'auth': 'https://api.dtes.mh.gob.sv/seguridad/auth',
            'recepcion': 'https://api.dtes.mh.gob.sv/fesv/recepciondte',
            'anulardte': 'https://api.dtes.mh.gob.sv/fesv/anulardte',
        },
        '01': {  # Pruebas
            'auth': 'https://apitest.dtes.mh.gob.sv/seguridad/auth',
            'recepcion': 'https://apitest.dtes.mh.gob.sv/fesv/recepciondte',
            'anulardte': 'https://apitest.dtes.mh.gob.sv/fesv/anulardte',
        }
    }

    # Convención DOBLE (confirmada con test real contra MH):
    # empresa.ambiente → URL MH:          '01'=apitest (PRUEBAS)  | '00'=api (PRODUCCIÓN)
    # empresa.ambiente → campo DTE/env:   '01'(PRUEBAS)→'00' DTE  | '00'(PROD)→'01' DTE
    # MH usa la convención inversa en el contenido del DTE respecto al campo empresa.ambiente
    DTE_AMBIENTE_CODE = {'01': '00', '00': '01'}
    
    # URL del firmador (configurable desde settings)
    URL_FIRMADOR = getattr(settings, 'DTE_FIRMADOR_URL', 'http://localhost:8113/firmardocumento/')
    
    def __init__(self, empresa: Empresa):
        """
        Inicializa el servicio con una empresa.
        
        Args:
            empresa: Instancia del modelo Empresa
            
        Raises:
            ValueError: Si la empresa no tiene credenciales configuradas
        """
        if not isinstance(empresa, Empresa):
            raise ValueError("Se requiere una instancia de Empresa")
        
        self.empresa = empresa
        
        # Validar que la empresa tenga credenciales básicas
        if not self.empresa.user_api_mh:
            raise ValueError("La empresa no tiene configurado user_api_mh")
        
        if not self.empresa.clave_api_mh:
            raise ValueError("La empresa no tiene configurado clave_api_mh")
        
        # Obtener URLs según el ambiente (00=Producción, 01=Pruebas)
        ambiente = self.empresa.ambiente or '01'  # Default a Pruebas ('01') por seguridad
        if ambiente not in self.URLS_MH:
            logger.warning(f"Ambiente '{ambiente}' no reconocido, usando '01' (Pruebas)")
            ambiente = '01'
        
        self.ambiente = ambiente
        self.url_auth = self.URLS_MH[ambiente]['auth']
        self.url_recepcion = self.URLS_MH[ambiente]['recepcion']
        self.url_anulardte = self.URLS_MH[ambiente]['anulardte']
        
        # El código de ambiente MH es el mismo que el valor del campo (ya viene como '00' o '01')
        self.codigo_ambiente_mh = ambiente
        
        ambiente_nombre = 'Producción' if ambiente == '00' else 'Pruebas'
        logger.info(f"FacturacionService inicializado para empresa: {empresa.nombre} (Ambiente: {ambiente} - {ambiente_nombre})")
        logger.info(f"   🔗 URL Auth: {self.url_auth}")
        logger.info(f"   🔗 URL Recepción: {self.url_recepcion}")
    
    def obtener_token(self) -> Optional[str]:
        """
        Obtiene el token de autenticación del Ministerio de Hacienda.
        
        Returns:
            Token de autenticación o None si falla
            
        Raises:
            AutenticacionMHError: Si hay un error en la autenticación
        """
        user = (self.empresa.user_api_mh or '').strip()
        pwd = (self.empresa.clave_api_mh or '').strip()
        # PRUEBA: si MH_PASSWORD_OVERRIDE está definido, usa ese valor para validar (ej: espacio en BD)
        override = getattr(settings, 'MH_PASSWORD_OVERRIDE', None)
        if override:
            logger.warning(f"⚠️ Usando MH_PASSWORD_OVERRIDE para prueba (pwd BD len={len(pwd)})")
            pwd = str(override).strip()
        if not user or not pwd:
            raise AutenticacionMHError("La empresa no tiene configuradas credenciales MH (user_api_mh y clave_api_mh)")
        # LOG de diagnóstico: muestra longitud y primeros/últimos 3 chars (NO expone password completa)
        logger.warning(f"🔑 AUTH MH → user='{user}' (len={len(user)}) | pwd_len={len(pwd)} | pwd_ini={repr(pwd[:3])} | pwd_fin={repr(pwd[-3:])}")
        payload = {
            "user": user,
            "pwd": pwd
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0"
        }
        
        try:
            logger.info(f"Autenticando con MH en {self.url_auth}...")
            resp = requests.post(self.url_auth, data=payload, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                datos = resp.json()
                token = datos.get("body", {}).get("token")
                
                if token:
                    logger.info("✅ Token de autenticación obtenido exitosamente")
                    return token
                else:
                    error_msg = f"Respuesta sin token: {datos}"
                    logger.error(f"❌ Error Auth: {error_msg}")
                    raise AutenticacionMHError(error_msg)
            else:
                error_msg = f"Error HTTP {resp.status_code}: {resp.text}"
                logger.error(f"❌ Error Auth: {error_msg}")
                raise AutenticacionMHError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión: {str(e)}"
            logger.error(f"❌ Error Conexión Auth: {error_msg}")
            raise AutenticacionMHError(error_msg) from e
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            logger.error(f"❌ Error inesperado en autenticación: {error_msg}")
            raise AutenticacionMHError(error_msg) from e
    
    def firmar_dte(self, json_dte: Dict[str, Any]) -> Optional[str]:
        """
        Firma digitalmente el documento DTE usando el servicio de firma.
        
        Args:
            json_dte: Diccionario con el JSON del DTE
            
        Returns:
            JWS firmado o None si falla
            
        Raises:
            FirmaDTEError: Si hay un error en la firma
        """
        # Validar que exista el certificado
        if not self.empresa.archivo_certificado:
            raise FirmaDTEError("La empresa no tiene configurado el archivo de certificado")
        
        if not self.empresa.clave_certificado:
            raise FirmaDTEError("La empresa no tiene configurada la clave del certificado")
        
        # Obtener NIT sin guiones
        nit_emisor = (self.empresa.nit or self.empresa.nrc or "").replace('-', '').replace(' ', '')
        use_internal = getattr(settings, 'USE_INTERNAL_FIRMADOR', False)

        if use_internal:
            # Firma interna: certificado MH (XML) + JWS RS512, sin contenedor firmador
            try:
                cert_path = Path(self.empresa.archivo_certificado.path)
                dte_json_str = json.dumps(json_dte, ensure_ascii=False)
                logger.info("Firmando documento DTE con firmador interno (Python)...")
                clave_cert = (self.empresa.clave_certificado or '').strip()
                jws_firmado = firmar_dte_interno(
                    cert_path,
                    clave_cert,
                    dte_json_str,
                    validar_password=True,
                )
                if jws_firmado:
                    logger.info("✅ Documento firmado correctamente (firmador interno)")
                    return jws_firmado
                raise FirmaDTEError("Firmador interno no devolvió JWS")
            except Exception as e:
                logger.exception("Error en firmador interno: %s", e)
                raise FirmaDTEError(str(e)) from e

        clave_cert = (self.empresa.clave_certificado or '').strip()
        payload = {
            "nit": nit_emisor,
            "activo": True,
            "passwordPri": clave_cert,
            "dteJson": json_dte
        }
        headers = {'Content-Type': 'application/json'}

        try:
            logger.info(f"Firmando documento DTE con firmador en {self.URL_FIRMADOR}...")
            resp = requests.post(self.URL_FIRMADOR, json=payload, headers=headers, timeout=60)
            
            if resp.status_code == 200:
                datos = resp.json()
                
                if datos.get("status") == "OK":
                    jws_firmado = datos.get("body")
                    if jws_firmado:
                        logger.info("✅ Documento firmado correctamente (JWS generado)")
                        return jws_firmado
                    else:
                        error_msg = "Respuesta sin JWS firmado"
                        logger.error(f"❌ Error Firmador: {error_msg}")
                        raise FirmaDTEError(error_msg)
                else:
                    error_msg = f"Error del firmador: {datos}"
                    logger.error(f"❌ Error Firmador: {error_msg}")
                    raise FirmaDTEError(error_msg)
            else:
                error_msg = f"Error HTTP {resp.status_code}: {resp.text}"
                logger.error(f"❌ Error Conexión Firmador: {error_msg}")
                raise FirmaDTEError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión con firmador: {str(e)}"
            logger.error(f"❌ Error Conexión Firmador: {error_msg}")
            raise FirmaDTEError(error_msg) from e
        except Exception as e:
            error_msg = f"Error inesperado en firma: {str(e)}"
            logger.error(f"❌ Error inesperado en firma: {error_msg}")
            raise FirmaDTEError(error_msg) from e
    
    def enviar_dte(self, dte_firmado: str, codigo_generacion: str, tipo_dte: str = '01') -> Dict[str, Any]:
        """
        Envía el DTE firmado al Ministerio de Hacienda.
        
        Args:
            dte_firmado: JWS firmado del documento
            codigo_generacion: Código único de generación (UUID)
            tipo_dte: Tipo de DTE ('01' para Factura, '03' para CCF)
            
        Returns:
            Diccionario con la respuesta de MH
            
        Raises:
            EnvioMHError: Si hay un error en el envío
        """
        # Obtener token primero
        token = self.obtener_token()
        if not token:
            raise EnvioMHError("No se pudo obtener el token de autenticación")
        
        # Estructura de envío: version del envelope según tipo DTE
        # DTE-01 (Factura CF) -> version 1 | DTE-03 (CCF) -> version 3
        version_envio = 1 if tipo_dte == '01' else 3
        # MH exige codigoGeneracion en MAYÚSCULAS
        codigo_upper = (codigo_generacion or "").upper()
        # DTE_AMBIENTE_CODE invierte: empresa='01'(Pruebas)→envelope='00' | empresa='00'(Prod)→'01'
        ambiente_envio = self.DTE_AMBIENTE_CODE.get(self.codigo_ambiente_mh, self.codigo_ambiente_mh)
        envio_mh = {
            "ambiente": ambiente_envio,
            "idEnvio": 1,
            "version": version_envio,
            "tipoDte": tipo_dte,
            "documento": dte_firmado,
            "codigoGeneracion": codigo_upper
        }
        
        headers_mh = {
            "Authorization": token,  # Token Bearer
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        try:
            logger.info(f"Enviando DTE a MH en {self.url_recepcion} (ambiente: {self.empresa.ambiente})...")
            resp = requests.post(self.url_recepcion, json=envio_mh, headers=headers_mh, timeout=60)
            
            logger.info(f"📡 Respuesta Servidor: {resp.status_code}")
            
            if resp.status_code in [200, 201]:
                datos = resp.json()
                estado = datos.get("estado")
                
                if estado == "PROCESADO":
                    sello = datos.get("selloRecibido")
                    logger.info(f"🎉 DTE PROCESADO EXITOSAMENTE - Sello: {sello}")
                    return {
                        "exito": True,
                        "estado": estado,
                        "sello_recibido": sello,
                        "codigo_generacion": codigo_generacion,
                        "mensaje": "DTE procesado correctamente",
                        "datos_completos": datos
                    }
                else:
                    mensaje = datos.get("descripcionMsg", "Sin mensaje")
                    observaciones = datos.get("observaciones", "Sin observaciones")
                    logger.warning(f"⚠️ DTE RECIBIDO PERO RECHAZADO: {mensaje}")
                    return {
                        "exito": False,
                        "estado": estado,
                        "mensaje": mensaje,
                        "observaciones": observaciones,
                        "datos_completos": datos
                    }
            else:
                error_msg = f"Error HTTP {resp.status_code}: {resp.text}"
                logger.error(f"❌ Error en el envío: {error_msg}")
                # 5xx = error transitorio del servidor MH
                if resp.status_code >= 500:
                    raise EnvioMHTransitorioError(error_msg) from None
                raise EnvioMHError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión enviando a MH: {str(e)}"
            logger.error(f"❌ Error Conexión MH: {error_msg}")
            raise EnvioMHTransitorioError(error_msg) from e
        except Exception as e:
            error_msg = f"Error inesperado enviando a MH: {str(e)}"
            logger.error(f"❌ Error inesperado: {error_msg}")
            raise EnvioMHError(error_msg) from e
    
    def procesar_factura(self, venta: Venta) -> Dict[str, Any]:
        """
        Procesa una factura completa: genera DTE, firma y envía a MH.
        
        Este es el método principal que orquesta todo el proceso.
        
        Args:
            venta: Instancia del modelo Venta a procesar
            
        Returns:
            Diccionario con el resultado del proceso:
            {
                "exito": bool,
                "venta_id": int,
                "codigo_generacion": str,
                "numero_control": str,
                "sello_recibido": str (si exitoso),
                "estado": str,
                "mensaje": str,
                "errores": list (si hay errores)
            }
            
        Raises:
            FacturacionServiceError: Si hay un error en cualquier paso
        """
        if not isinstance(venta, Venta):
            raise ValueError("Se requiere una instancia de Venta")
        
        if venta.empresa != self.empresa:
            raise ValueError("La venta no pertenece a la empresa del servicio")
        
        logger.info(f"🚀 INICIANDO PROCESO DE FACTURACIÓN ELECTRÓNICA para venta #{venta.id}")
        
        resultado = {
            "exito": False,
            "venta_id": venta.id,
            "codigo_generacion": None,
            "numero_control": None,
            "sello_recibido": None,
            "estado": None,
            "mensaje": None,
            "errores": []
        }
        
        try:
            # PASO 1: Generar JSON DTE usando director (Patrón Strategy)
            logger.info("1. Generando JSON DTE...")
            # DTE_AMBIENTE_CODE invierte: empresa='01'(Pruebas)→DTE='00' | empresa='00'(Prod)→DTE='01'
            ambiente_dte = self.DTE_AMBIENTE_CODE.get(self.codigo_ambiente_mh, self.codigo_ambiente_mh)
            json_dte = generar_dte(venta, ambiente=ambiente_dte)
            logger.info(f"   🌐 empresa.ambiente={self.codigo_ambiente_mh} → DTE ambiente={ambiente_dte}")
            
            # Obtener código de generación y número de control (MH exige MAYÚSCULAS)
            codigo_generacion = (venta.codigo_generacion or json_dte['identificacion']['codigoGeneracion'] or '').upper()
            numero_control = venta.numero_control or json_dte['identificacion']['numeroControl']
            
            resultado["codigo_generacion"] = codigo_generacion
            resultado["numero_control"] = numero_control
            
            logger.info(f"   ✅ DTE generado (UUID: {codigo_generacion}, Control: {numero_control})")
            
            # PASO 2: Firmar documento
            logger.info("2. Firmando documento...")
            dte_firmado = self.firmar_dte(json_dte)
            
            if not dte_firmado:
                raise FirmaDTEError("No se pudo obtener el JWS firmado")
            
            logger.info("   ✅ Documento firmado correctamente")
            
            # PASO 3: Enviar a MH
            logger.info("3. Enviando a Ministerio de Hacienda...")
            tmap = {'CF': '01', 'CCF': '03', 'NC': '05', 'ND': '06'}
            tipo_dte = tmap.get(venta.tipo_venta, '03')
            respuesta_mh = self.enviar_dte(dte_firmado, codigo_generacion, tipo_dte)
            
            # Actualizar resultado con la respuesta de MH
            resultado.update(respuesta_mh)
            
            # Si fue exitoso, actualizar la venta
            if respuesta_mh.get("exito"):
                venta.estado_dte = 'AceptadoMH'
                venta.sello_recepcion = respuesta_mh.get("sello_recibido")
                venta.codigo_generacion = codigo_generacion
                venta.numero_control = numero_control
                venta.hora_emision = json_dte.get('identificacion', {}).get('horEmi') or venta.hora_emision
                venta.save()
                
                logger.info(f"🎉🎉🎉 ¡ÉXITO TOTAL! FACTURA #{venta.id} ACEPTADA 🎉🎉🎉")
            else:
                venta.estado_dte = 'RechazadoMH'
                import json
                datos = respuesta_mh.get('datos_completos') or {}
                codigo = datos.get('codigoMsg', datos.get('codigo'))
                desc = respuesta_mh.get('mensaje', datos.get('descripcionMsg', ''))
                obs = respuesta_mh.get('observaciones')
                obs_list = obs if isinstance(obs, list) else ([str(obs)] if obs else [])
                venta.observaciones_mh = json.dumps({
                    'codigo': codigo,
                    'descripcion': desc,
                    'observaciones': obs_list
                })
                venta.save()
                logger.warning(f"⚠️ FACTURA #{venta.id} RECHAZADA POR MH")
            
            return resultado
            
        except AutenticacionMHError as e:
            error_msg = f"Error de autenticación: {str(e)}"
            logger.error(error_msg)
            resultado["errores"].append(error_msg)
            resultado["mensaje"] = error_msg
            venta.estado_dte = 'Borrador'  # Mantener en borrador si falla auth
            venta.save()
            raise FacturacionServiceError(error_msg) from e
            
        except FirmaDTEError as e:
            error_msg = f"Error de firma: {str(e)}"
            logger.error(error_msg)
            resultado["errores"].append(error_msg)
            resultado["mensaje"] = error_msg
            venta.estado_dte = 'Borrador'
            venta.save()
            raise FacturacionServiceError(error_msg) from e
            
        except EnvioMHTransitorioError as e:
            error_msg = f"Error transitorio de envío (MH no disponible): {str(e)}"
            logger.warning(error_msg)
            resultado["errores"].append(error_msg)
            resultado["mensaje"] = "MH no disponible. La factura quedó pendiente de envío."
            venta.estado_dte = 'PendienteEnvio'
            venta.error_envio_mensaje = str(e)[:500]
            venta.save()
            raise FacturacionServiceError(error_msg) from e
        except EnvioMHError as e:
            error_msg = f"Error de envío: {str(e)}"
            logger.error(error_msg)
            resultado["errores"].append(error_msg)
            resultado["mensaje"] = error_msg
            venta.estado_dte = 'RechazadoMH'
            venta.observaciones_mh = error_msg
            venta.save()
            raise FacturacionServiceError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            logger.error(error_msg)
            resultado["errores"].append(error_msg)
            resultado["mensaje"] = error_msg
            venta.estado_dte = 'Borrador'
            venta.save()
            raise FacturacionServiceError(error_msg) from e

    def invalidar_dte(self, venta: Venta, datos_invalidacion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invalida (anula) un DTE ya emitido según esquema anulacion-schema-v2 de MH.

        Args:
            venta: Instancia de Venta con sello_recepcion (documento procesado por MH)
            datos_invalidacion: Dict con motivo, responsable, solicitante, tipoInvalidacion,
                               codigoGeneracionDocumentoReemplazo (null para Rescisión)

        Returns:
            Dict con exito, mensaje, datos_completos
        """
        import re
        import uuid
        from datetime import datetime

        if not venta.codigo_generacion:
            raise FacturacionServiceError("La venta no tiene código de generación")
        if not venta.sello_recepcion:
            raise FacturacionServiceError("Solo se pueden invalidar documentos ya procesados por MH")
        if not venta.empresa:
            raise FacturacionServiceError("La venta no tiene empresa asociada")

        empresa = venta.empresa
        tipo_dte = '01' if venta.tipo_venta == 'CF' else '03'
        resp = datos_invalidacion.get('responsable', {})
        sol = datos_invalidacion.get('solicitante', {})
        tipo_inv_str = datos_invalidacion.get('tipoInvalidacion', 'Rescisión')
        motivo = (datos_invalidacion.get('motivoInvalidacion') or '').strip() or 'Solicitud del contribuyente'
        codigo_reemplazo = datos_invalidacion.get('codigoGeneracionDocumentoReemplazo')

        # CAT-22: NIT=36, DUI=13, Carnet=02, Pasaporte=03, Otro=37
        def cat22(tipo: str) -> str:
            t = (tipo or 'NIT').upper()
            return '36' if t == 'NIT' else '13' if t == 'DUI' else '37'

        # Hora real de El Salvador (UTC-6)
        from datetime import timedelta, timezone
        tz_sv = timezone(timedelta(hours=-6))
        ahora_sv = datetime.now(tz_sv)
        fec_anula = ahora_sv.strftime('%Y-%m-%d')
        hor_anula = ahora_sv.strftime('%H:%M:%S')

        # UUID nuevo para el documento de anulación (identificacion.codigoGeneracion)
        codigo_anulacion = str(uuid.uuid4()).upper()

        # Sello sin guiones, 40 caracteres exactos
        sello_limpio = (venta.sello_recepcion or '').replace('-', '').replace(' ', '').upper()
        if len(sello_limpio) != 40:
            raise FacturacionServiceError(
                f"El sello de recepción debe tener 40 caracteres (actual: {len(sello_limpio)})"
            )

        # Emisor desde empresa (NIT 9 o 14 dígitos sin guiones, según schema MH)
        nit_raw = re.sub(r'[^0-9]', '', (empresa.nit or empresa.nrc or '000000000'))
        nit_limpio = (nit_raw[:14] if len(nit_raw) >= 14 else nit_raw.zfill(9)) or '000000000'
        nom_estab = (empresa.nombre or '')[:150] or 'Establecimiento'
        cod_estab = (empresa.cod_establecimiento or 'M001')[:10]
        cod_pv = (empresa.cod_punto_venta or 'P001')[:15]
        tel_emp = (empresa.telefono or '00000000')[:26]
        if not tel_emp or len(tel_emp) < 8:
            tel_emp = '00000000'
        correo_emp = (empresa.correo or 'contacto@empresa.sv')[:100]

        # Receptor: tipoDocumento y numDocumento deben coincidir EXACTAMENTE con el DTE original (MH)
        tipo_doc_recep = None
        num_doc_recep = None
        cliente = venta.cliente
        if tipo_dte == '03' and cliente:
            nit_cli = (cliente.nit or cliente.nrc or "").replace("-", "").replace(" ", "")
            if nit_cli and len(nit_cli) >= 3:
                tipo_doc_recep = "36"
                num_doc_recep = nit_cli.zfill(14)[:20]
        elif tipo_dte == '01':
            if cliente:
                nit_cli = (cliente.nit or "").replace("-", "").replace(" ", "").strip()
                dui_cli = (cliente.dui or "").replace("-", "").replace(" ", "").strip()
                if nit_cli:
                    tipo_doc_recep, num_doc_recep = "36", nit_cli.zfill(14)[:20]
                elif dui_cli:
                    tipo_doc_recep, num_doc_recep = "13", dui_cli.zfill(14)[:20]
            # CF sin cliente o cliente sin nit/dui: documento_receptor o null (Consumidor genérico)
            doc_cf = (venta.documento_receptor or venta.nrc_receptor or "").replace("-", "").replace(" ", "").strip()
            if doc_cf and len(doc_cf) >= 3 and not num_doc_recep:
                tdoc = (venta.tipo_doc_receptor or "NIT").upper()
                tipo_doc_recep = "36" if tdoc == "NIT" else "13"
                num_doc_recep = doc_cf.zfill(14)[:20]

        nombre_recep = (venta.nombre_receptor or 'Consumidor Final').strip() or 'Consumidor Final'
        if len(nombre_recep) < 5:
            nombre_recep = 'Consumidor Final'

        # tipoAnulacion: 1=?, 2=Rescisión (codigoGeneracionR null), 3=Nulidad
        tipo_anulacion = 2 if tipo_inv_str == 'Rescisión' else (3 if tipo_inv_str == 'Nulidad' else 2)
        if tipo_anulacion == 2:
            codigo_reemplazo = None
        elif not codigo_reemplazo:
            codigo_reemplazo = '00000000-0000-0000-0000-000000000000'  # placeholder si tipo 1/3
        else:
            codigo_reemplazo = str(codigo_reemplazo).upper()

        nombre_resp = (resp.get('nombre') or '').strip()
        if len(nombre_resp) < 5:
            nombre_resp = empresa.nombre[:100] if empresa.nombre else 'Responsable'
        num_doc_resp = str(resp.get('numeroDocumento') or '').replace('-', '').replace(' ', '')
        if len(num_doc_resp) < 3:
            num_doc_resp = nit_limpio[:20] if nit_limpio else '00000000000000'

        nombre_sol = (sol.get('nombre') or '').strip()
        if len(nombre_sol) < 5:
            nombre_sol = nombre_resp
        num_doc_sol = str(sol.get('numeroDocumento') or '').replace('-', '').replace(' ', '')
        if len(num_doc_sol) < 3:
            num_doc_sol = num_doc_resp

        # Estructura según anulacion-schema-v2.json
        ambiente_dte = self.DTE_AMBIENTE_CODE.get(self.codigo_ambiente_mh, self.codigo_ambiente_mh)
        evento = {
            "identificacion": {
                "version": 2,
                "ambiente": ambiente_dte,
                "codigoGeneracion": codigo_anulacion,
                "fecAnula": fec_anula,
                "horAnula": hor_anula,
            },
            "emisor": {
                "nit": nit_limpio,
                "nombre": (empresa.nombre or 'Empresa')[:250],
                "tipoEstablecimiento": "01",
                "nomEstablecimiento": nom_estab,
                "codEstableMH": (empresa.cod_establecimiento or 'M001')[:4],
                "codEstable": cod_estab,
                "codPuntoVentaMH": (empresa.cod_punto_venta or 'P001')[:4],
                "codPuntoVenta": cod_pv,
                "telefono": tel_emp,
                "correo": correo_emp,
            },
            "documento": {
                "tipoDte": tipo_dte,
                "codigoGeneracion": (venta.codigo_generacion or "").upper(),
                "selloRecibido": sello_limpio,
                "numeroControl": (venta.numero_control or '')[:31],
                "fecEmi": venta.fecha_emision.strftime('%Y-%m-%d') if venta.fecha_emision else fec_anula,
                "montoIva": round(float(venta.debito_fiscal or 0), 2),
                "codigoGeneracionR": codigo_reemplazo,
                "tipoDocumento": tipo_doc_recep,
                "numDocumento": num_doc_recep,
                "nombre": nombre_recep[:200],
            },
            "motivo": {
                "tipoAnulacion": tipo_anulacion,
                "motivoAnulacion": motivo[:250] if motivo else "Solicitud del contribuyente",
                "nombreResponsable": nombre_resp[:100],
                "tipDocResponsable": cat22(resp.get('tipoDocumento')),
                "numDocResponsable": num_doc_resp[:20],
                "nombreSolicita": nombre_sol[:100],
                "tipDocSolicita": cat22(sol.get('tipoDocumento')),
                "numDocSolicita": num_doc_sol[:20],
            },
        }

        logger.info(f"Invalidando DTE venta #{venta.id} ({venta.codigo_generacion}) - Hora SV: {fec_anula} {hor_anula}")

        evento_firmado = self.firmar_dte(evento)
        if not evento_firmado:
            raise FirmaDTEError("No se pudo firmar el evento de invalidación")

        token = self.obtener_token()
        if not token:
            raise EnvioMHError("No se pudo obtener token de autenticación")

        # Envelope para recepcionevento (todo minúsculas, requerido por MH)
        payload = {
            "ambiente": self.DTE_AMBIENTE_CODE.get(self.codigo_ambiente_mh, self.codigo_ambiente_mh),
            "idEnvio": 1,
            "version": 2,
            "tipoDte": tipo_dte,
            "tipoEvento": "invalidacion",
            "documento": evento_firmado,
            "codigoGeneracion": codigo_anulacion,
        }

        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        # DTE_ANULAR_URL: override en settings si necesario. Manual MH 4.5: anulardte
        url_envio = getattr(settings, 'DTE_ANULAR_URL', None) or self.url_anulardte

        try:
            logger.info(f"Enviando evento de invalidación a {url_envio}...")
            resp_mh = requests.post(url_envio, json=payload, headers=headers, timeout=60)
            logger.info(f"Respuesta MH: {resp_mh.status_code}")

            if resp_mh.status_code in [200, 201]:
                datos = resp_mh.json()
                estado = datos.get("estado", "")
                if estado == "PROCESADO":
                    venta.estado_dte = 'Anulado'
                    venta.save()
                    logger.info(f"DTE venta #{venta.id} anulado exitosamente")
                    return {
                        "exito": True,
                        "mensaje": "Documento invalidado correctamente",
                        "datos_completos": datos,
                    }
                else:
                    return {
                        "exito": False,
                        "mensaje": datos.get("descripcionMsg", "Evento rechazado"),
                        "observaciones": datos.get("observaciones", []),
                        "datos_completos": datos,
                    }
            else:
                error_msg = f"Error HTTP {resp_mh.status_code}: {resp_mh.text}"
                raise EnvioMHError(error_msg)
        except requests.exceptions.RequestException as e:
            raise EnvioMHError(f"Error de conexión: {str(e)}") from e

