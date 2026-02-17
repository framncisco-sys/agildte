"""
Firmador interno para DTE MH El Salvador.
Parsea certificados en formato XML de MH, extrae la clave privada y firma el JSON con JWS RS512.
Compatible con el formato usado por GoFirmadorDTE-SV (encodied en base64, clave = SHA512 hex del password).
"""
import base64
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

# Solo caracteres válidos en base64 estándar
_B64_RE = re.compile(r"[A-Za-z0-9+/=]+")

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.serialization import (
        load_der_private_key,
        load_pem_private_key,
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
    load_pem_private_key = None
    Encoding = None
    PrivateFormat = None
    NoEncryption = None


def _sha512_hex(password: str) -> str:
    return hashlib.sha512(password.encode("utf-8")).hexdigest()


def _normalize_tag(tag: str) -> str:
    """Quita namespace XML si existe (ej: '{uri}privateKey' -> 'privatekey')."""
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    return tag.lower()


def _find_element(parent, *names: str):
    """Busca hijo por nombre (sin importar mayúsculas ni namespace)."""
    for child in parent:
        if _normalize_tag(child.tag) in [n.lower() for n in names]:
            return child
    for name in names:
        found = parent.find(name)
        if found is not None:
            return found
    return None


def _get_text(elem) -> Optional[str]:
    if elem is None or elem.text is None:
        return None
    return elem.text.strip() or None


def _parse_certificado_mh_xml(path: Path) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Parsea el XML del certificado MH y devuelve (private_key_bytes, clave_hex).
    La clave privada está en <privateKey><encodied> (base64). La validación del password
    es <privateKey><clave> = SHA512(password) en hex.
    """
    try:
        with open(path, "rb") as f:
            raw = f.read()
        # Intentar varios encodings
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                root = ET.fromstring(raw.decode(encoding))
                break
            except UnicodeDecodeError:
                continue
        else:
            root = ET.fromstring(raw.decode("utf-8", errors="replace"))
    except ET.ParseError as e:
        logger.exception("XML del certificado inválido: %s", e)
        return None, None
    except Exception as e:
        logger.exception("Error leyendo certificado: %s", e)
        return None, None

    # Buscar bloque privateKey (puede ser privateKey, PrivateKey o con namespace)
    priv = None
    for child in root:
        if _normalize_tag(child.tag) == "privatekey":
            priv = child
            break
    if priv is None:
        priv = root.find("privateKey") or root.find("PrivateKey")
    if priv is None:
        # Último intento: buscar en todo el árbol (por si está anidado)
        for elem in root.iter():
            if _normalize_tag(elem.tag) == "privatekey":
                priv = elem
                break
    if priv is None:
        logger.warning("No se encontró elemento privateKey en el certificado XML")
        return None, None

    # Buscar encodied (contenido base64 de la clave); reunir todo el texto del nodo
    encodied_el = _find_element(priv, "encodied", "Encodied")
    if encodied_el is None:
        for elem in priv.iter():
            if _normalize_tag(elem.tag) == "encodied":
                encodied_el = elem
                break
    encodied_text = None
    if encodied_el is not None:
        # Reunir todo el texto del nodo (por si el parser parte el contenido)
        encodied_text = "".join(encodied_el.itertext()) or _get_text(encodied_el) or (encodied_el.text or "")
        encodied_text = (encodied_text or "").strip().replace("\n", "").replace("\r", "").replace(" ", "").replace("\t", "")
    if not encodied_text:
        logger.warning("No se encontró encodied dentro de privateKey")
        return None, None

    clave_el = _find_element(priv, "clave", "Clave")
    clave_hex = _get_text(clave_el) if clave_el is not None else None

    try:
        b64_clean = encodied_text.replace("\n", "").replace("\r", "").replace(" ", "").replace("\t", "")
        # Dejar solo caracteres base64 (por si hay caracteres raros en el XML)
        b64_clean = "".join(_B64_RE.findall(b64_clean))
        key_bytes = base64.b64decode(b64_clean)
    except Exception as e:
        logger.exception("Error decodificando base64 de encodied: %s", e)
        return None, None

    if not key_bytes:
        return None, None
    return key_bytes, clave_hex


def _key_bytes_to_jwk_rsa(key_bytes: bytes) -> Optional[jwk.JWK]:
    """Convierte clave privada (DER o PEM) a JWK para usar con jwcrypto."""
    if not CRYPTO_AVAILABLE:
        return None
    backend = default_backend()
    key_bytes = key_bytes.strip()
    # Quitar BOM UTF-8 si existe (no tocar 0x00 dentro del DER)
    if key_bytes.startswith(b"\xef\xbb\xbf"):
        key_bytes = key_bytes[3:]
    key = None
    try:
        if key_bytes.startswith(b"-----BEGIN"):
            key = load_pem_private_key(key_bytes, password=None, backend=backend)
        else:
            # DER: si hay basura antes del SEQUENCE (0x30), buscar el inicio real
            if not key_bytes.startswith(b"\x30"):
                idx = key_bytes.find(b"\x30")
                if idx >= 0:
                    key_bytes = key_bytes[idx:]
            key = load_der_private_key(key_bytes, password=None, backend=backend)
    except Exception as e1:
        logger.warning("Carga DER falló (%s), intentando como PEM...", e1)
        try:
            # Algunos certificados MH guardan PEM en base64 dentro de encodied
            key = load_pem_private_key(key_bytes, password=None, backend=backend)
        except Exception as e2:
            logger.exception("Error cargando clave privada (DER/PEM): %s / %s", e1, e2)
            return None
    if key is None:
        return None
    try:
        pem = key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        return jwk.JWK.from_pem(pem)
    except Exception as e:
        logger.exception("Error convirtiendo clave a JWK: %s", e)
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
    key_bytes, clave_hex = _parse_certificado_mh_xml(path_certificado)
    if not key_bytes:
        raise ValueError(
            "No se pudo extraer la clave privada del certificado XML. "
            "Verifica que el archivo sea el .crt descargado del portal de MH (formato XML con <CertificadoMH><privateKey><encodied>...). "
            "Si lo subiste por la app, prueba descargarlo de nuevo de factura.gob.sv y volver a cargarlo."
        )
    if validar_password and clave_hex and _sha512_hex(password) != clave_hex:
        raise ValueError("Password del certificado no válido")
    jwk_key = _key_bytes_to_jwk_rsa(key_bytes)
    if not jwk_key:
        raise ValueError(
            "No se pudo cargar la clave RSA desde el certificado. "
            "El contenido de <encodied> debe ser base64 de una clave PKCS#8 (DER) o PEM."
        )
    # Payload: el JSON tal cual (string). JWS compacto con RS512.
    payload_bytes = dte_json.encode("utf-8") if isinstance(dte_json, str) else dte_json
    jws_obj = jws.JWS(payload_bytes)
    jws_obj.add_signature(jwk_key, None, json_encode({"alg": "RS512"}), None)
    return jws_obj.serialize(compact=True)
