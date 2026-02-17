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


def _extract_encodied_and_clave_from_raw(raw_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae el contenido de <privateKey><encodied> y <clave> con regex sobre el texto crudo.
    Usamos el encodied que va seguido de <format>PKCS#8</format> para no confundir con la clave pública.
    """
    # Bloque privateKey (solo hay uno; contiene PKCS#8)
    priv_block = re.search(
        r"<[Pp]rivate[Kk]ey>([\s\S]*?)</[Pp]rivate[Kk]ey>",
        raw_text,
        re.DOTALL,
    )
    if not priv_block:
        return None, None
    block = priv_block.group(1)
    # Encodied de la clave PRIVADA: el que va seguido de <format>PKCS#8</format> (no X.509)
    enc = re.search(
        r"<[Ee]ncodied>([\s\S]*?)</[Ee]ncodied>\s*<[Ff]ormat>PKCS#8</[Ff]ormat>",
        block,
        re.DOTALL,
    )
    if not enc:
        enc = re.search(r"<[Ee]ncodied>([\s\S]*?)</[Ee]ncodied>", block, re.DOTALL)
    encodied = (enc.group(1).strip() if enc else None) or None
    cla = re.search(r"<[Cc]lave>([^<]+)</[Cc]lave>", block)
    clave_hex = (cla.group(1).strip() if cla else None) or None
    return encodied, clave_hex


def _parse_certificado_mh_xml(path: Path) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Parsea el certificado MH y devuelve (private_key_bytes, clave_hex).
    Usa regex sobre el archivo crudo para extraer <encodied> completo (evita truncado del parser XML).
    """
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception as e:
        logger.exception("Error leyendo certificado: %s", e)
        return None, None

    logger.warning("[FIRMADOR] Certificado leído: %d bytes, ruta=%s", len(raw), path)
    raw_text = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            raw_text = raw.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if raw_text is None:
        raw_text = raw.decode("utf-8", errors="replace")

    encodied_text, clave_hex = _extract_encodied_and_clave_from_raw(raw_text)
    if not encodied_text:
        logger.warning("[FIRMADOR] Regex no encontró encodied, usando fallback XML")
        # Fallback: parser XML
        try:
            root = ET.fromstring(raw_text.encode("utf-8") if isinstance(raw_text, str) else raw_text)
        except Exception:
            root = ET.fromstring(raw)
        priv = root.find("privateKey") or root.find("PrivateKey")
        if priv is not None:
            enc_el = priv.find("encodied") or priv.find("Encodied")
            if enc_el is not None and (enc_el.text or "".join(enc_el.itertext())):
                encodied_text = (enc_el.text or "") + "".join(enc_el.itertext())
            clave_el = priv.find("clave") or priv.find("Clave")
            if clave_hex is None and clave_el is not None and clave_el.text:
                clave_hex = clave_el.text.strip()
        if not encodied_text:
            logger.warning("No se encontró encodied en el certificado")
            return None, None

    encodied_text = (encodied_text or "").strip().replace("\n", "").replace("\r", "").replace(" ", "").replace("\t", "")
    b64_clean = "".join(_B64_RE.findall(encodied_text))
    pad = 4 - len(b64_clean) % 4
    if pad != 4:
        b64_clean += "=" * pad
    try:
        key_bytes = base64.b64decode(b64_clean)
    except Exception:
        try:
            key_bytes = base64.urlsafe_b64decode(b64_clean + ("=" * (4 - len(b64_clean) % 4) if len(b64_clean) % 4 else ""))
        except Exception as e:
            logger.exception("Error decodificando base64: %s", e)
            return None, None

    if not key_bytes:
        return None, None
    # RSA 2048 PKCS#8 DER suele ser ~1217 bytes; si es mucho menor, el archivo pudo truncarse
    logger.warning("[FIRMADOR] Clave privada decodificada: %d bytes (esperado ~1217)", len(key_bytes))
    if len(key_bytes) < 500:
        logger.warning(
            "[FIRMADOR] Clave muy corta: probable truncado al subir el certificado.",
        )
    return key_bytes, clave_hex


def _key_bytes_to_jwk_rsa(key_bytes: bytes, password: Optional[str] = None) -> Optional[jwk.JWK]:
    """Convierte clave privada (DER o PEM) a JWK. Prueba con y sin contraseña si viene cifrada."""
    if not CRYPTO_AVAILABLE:
        return None
    backend = default_backend()
    # No hacer .strip() en bytes DER: puede quitar bytes válidos y causar "short data"
    if key_bytes.startswith(b"-----BEGIN"):
        key_bytes = key_bytes.strip()
    elif key_bytes.startswith(b"\xef\xbb\xbf"):
        key_bytes = key_bytes[3:]
    key = None
    password_bytes = password.encode("utf-8") if password else None
    for pwd in (None, password_bytes):
        try:
            if key_bytes.startswith(b"-----BEGIN"):
                key = load_pem_private_key(key_bytes, password=pwd, backend=backend)
            else:
                der = key_bytes
                if not der.startswith(b"\x30"):
                    idx = der.find(b"\x30")
                    if idx >= 0:
                        der = der[idx:]
                key = load_der_private_key(der, password=pwd, backend=backend)
            if key is not None:
                break
        except Exception as e1:
            if pwd is None:
                logger.debug("Carga sin contraseña falló: %s", e1)
            else:
                logger.warning("Carga con contraseña falló: %s", e1)
    # Cryptography 45+ rechaza DER con bytes nulos al final; intentar sin ellos
    if key is None and not key_bytes.startswith(b"-----") and key_bytes.rstrip(b"\x00") != key_bytes:
        der_trim = key_bytes.rstrip(b"\x00")
        for pwd in (None, password_bytes):
            try:
                key = load_der_private_key(der_trim, password=pwd, backend=backend)
                if key is not None:
                    break
            except Exception:
                pass
    if key is None:
        try:
            key = load_pem_private_key(key_bytes, password=password_bytes, backend=backend)
        except Exception as e2:
            logger.warning("Carga PEM falló: %s", e2)
    # Último intento: encodied podría ser base64 de una cadena PEM (texto)
    if key is None and not key_bytes.startswith(b"\x30") and not key_bytes.startswith(b"-----"):
        try:
            pem_str = key_bytes.decode("utf-8", errors="ignore").strip()
            if "BEGIN" in pem_str:
                key = load_pem_private_key(pem_str.encode(), password=password_bytes, backend=backend)
        except Exception as e3:
            logger.debug("Intentar como PEM texto falló: %s", e3)
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
    jwk_key = _key_bytes_to_jwk_rsa(key_bytes, password=password)
    if not jwk_key:
        raise ValueError(
            "No se pudo cargar la clave RSA desde el certificado. "
            "Asegúrate de usar el archivo .crt tal cual lo descargas del portal de MH (factura.gob.sv), "
            "sin abrirlo ni guardarlo con otro programa. Vuelve a descargarlo y súbelo de nuevo en la empresa."
        )
    # Payload: el JSON tal cual (string). JWS compacto con RS512.
    payload_bytes = dte_json.encode("utf-8") if isinstance(dte_json, str) else dte_json
    jws_obj = jws.JWS(payload_bytes)
    jws_obj.add_signature(jwk_key, None, json_encode({"alg": "RS512"}), None)
    return jws_obj.serialize(compact=True)
