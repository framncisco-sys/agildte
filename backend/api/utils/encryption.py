"""
Utilidades de cifrado para datos sensibles (claves API, certificados, SMTP).
Usa Fernet (symmetric encryption) de la librería cryptography.
"""
import base64
import hashlib
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    """Obtiene instancia de Fernet con clave derivada de SECRET_KEY o FERNET_KEY."""
    global _fernet
    if _fernet is not None:
        return _fernet
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        logger.warning("cryptography no instalado; datos sensibles en texto plano")
        return None

    key = getattr(settings, 'FERNET_ENCRYPTION_KEY', None)
    if not key:
        # Derivar clave de SECRET_KEY para compatibilidad
        secret = settings.SECRET_KEY.encode('utf-8') if isinstance(settings.SECRET_KEY, str) else settings.SECRET_KEY
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'agildte_salt_v1',
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret))
    elif isinstance(key, str):
        key = key.encode('utf-8')

    try:
        _fernet = Fernet(key)
    except Exception as e:
        logger.warning(f"No se pudo inicializar Fernet: {e}")
        _fernet = None
    return _fernet


def encrypt_value(plain: Optional[str]) -> Optional[str]:
    """Cifra un valor en texto plano. None y '' devuelven None."""
    if plain is None or plain == '':
        return None
    f = _get_fernet()
    if not f:
        return plain
    try:
        encrypted = f.encrypt(plain.encode('utf-8'))
        return encrypted.decode('ascii')
    except Exception as e:
        logger.error(f"Error al cifrar: {e}")
        return plain


def decrypt_value(cipher: Optional[str]) -> Optional[str]:
    """
    Descifra un valor. Si falla (dato legacy en texto plano), devuelve el valor original.
    None y '' devuelven None.
    """
    if cipher is None or cipher == '':
        return None
    f = _get_fernet()
    if not f:
        return cipher
    try:
        decrypted = f.decrypt(cipher.encode('ascii'))
        return decrypted.decode('utf-8')
    except Exception:
        # Dato en texto plano (legacy) o corrupto
        return cipher
