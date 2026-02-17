"""
Firmador interno para DTE MH El Salvador.
Parsea certificados en formato XML de MH, extrae la clave privada y firma el JSON con JWS RS512.
Compatible con el formato usado por GoFirmadorDTE-SV (encodied en base64, clave = SHA512 hex del password).
"""
import base64
import hashlib
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.serialization import (
        load_der_private_key,
        Encoding,
        PrivateFormat,
        NoEncryption,
    )
    from cryptography.hazmat.backends import default_backend
    from jwcrypto import jws, jwk
    from jwcrypto.common import json_encode
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    load_der_private_key = None
    Encoding = None
    PrivateFormat = None
    NoEncryption = None


def _sha512_hex(password: str) -> str:
    return hashlib.sha512(password.encode("utf-8")).hexdigest()


def _parse_certificado_mh_xml(path: Path) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Parsea el XML del certificado MH y devuelve (private_key_der_bytes, clave_hex).
    La clave privada está en <privateKey><encodied> (base64). La validación del password
    es <privateKey><clave> = SHA512(password) en hex.
    """
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as e:
        logger.exception("Error parseando XML del certificado: %s", e)
        return None, None

    # Nombres pueden variar (PrivateKey vs privateKey)
    for tag in ("privateKey", "PrivateKey"):
        priv = root.find(tag)
        if priv is not None:
            encodied = priv.find("encodied") or priv.find("Encodied")
            clave = priv.find("clave") or priv.find("Clave")
            if encodied is not None and encodied.text:
                try:
                    key_bytes = base64.b64decode(encodied.text.strip().replace("\n", ""))
                    clave_hex = clave.text.strip() if clave is not None and clave.text else None
                    return key_bytes, clave_hex
                except Exception as e:
                    logger.exception("Error decodificando encodied: %s", e)
                    return None, None
    return None, None


def _der_to_jwk_rsa(der_bytes: bytes) -> Optional[jwk.JWK]:
    """Convierte clave privada DER a JWK para usar con jwcrypto."""
    if not CRYPTO_AVAILABLE:
        return None
    try:
        key = load_der_private_key(der_bytes, password=None, backend=default_backend())
        pem = key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        return jwk.JWK.from_pem(pem)
    except Exception as e:
        logger.exception("Error cargando clave DER: %s", e)
        return None


def validar_password_certificado(path_certificado: Path, password: str) -> bool:
    """Comprueba si el password coincide con el hash guardado en el certificado MH."""
    _, clave_hex = _parse_certificado_mh_xml(path_certificado)
    if not clave_hex:
        return False
    return _sha512_hex(password) == clave_hex


def firmar_dte_interno(
    path_certificado: Path,
    password: str,
    dte_json: str,
    validar_password: bool = True,
) -> str:
    """
    Firma el JSON DTE con el certificado MH (formato XML).
    Usa algoritmo RS512 como en GoFirmadorDTE-SV.
    Devuelve el JWS en formato compacto (header.payload.signature).
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError(
            "Firmador interno requiere: pip install cryptography jwcrypto"
        )
    if not path_certificado.exists():
        raise FileNotFoundError(f"Certificado no encontrado: {path_certificado}")
    key_der, clave_hex = _parse_certificado_mh_xml(path_certificado)
    if not key_der:
        raise ValueError("No se pudo extraer la clave privada del certificado XML")
    if validar_password and clave_hex and _sha512_hex(password) != clave_hex:
        raise ValueError("Password del certificado no válido")
    jwk_key = _der_to_jwk_rsa(key_der)
    if not jwk_key:
        raise ValueError("No se pudo cargar la clave RSA desde el certificado")
    # Payload: el JSON tal cual (string). JWS compacto con RS512.
    payload_bytes = dte_json.encode("utf-8") if isinstance(dte_json, str) else dte_json
    jws_obj = jws.JWS(payload_bytes)
    jws_obj.add_signature(jwk_key, None, json_encode({"alg": "RS512"}), None, None)
    return jws_obj.serialize(compact=True)
