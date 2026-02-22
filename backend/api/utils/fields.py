"""
Campos personalizados para Django (cifrado, etc.).
"""
from django.db import models

from .encryption import decrypt_value, encrypt_value


class EncryptedTextField(models.TextField):
    """
    TextField que cifra el valor antes de guardar y descifra al leer.
    Compatible con datos legacy en texto plano (si el descifrado falla, devuelve el valor original).
    Strip automático al guardar y al leer para evitar espacios ocultos en contraseñas.
    """
    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        decrypted = decrypt_value(value)
        if isinstance(decrypted, str):
            return decrypted.strip() or None
        return decrypted

    def get_prep_value(self, value):
        if value is None or value == '':
            return None
        clean = str(value).strip()
        if not clean:
            return None
        return encrypt_value(clean)


class EncryptedCharField(models.CharField):
    """
    CharField que cifra el valor antes de guardar y descifra al leer.
    Usar max_length generoso (ej: 500) porque el base64 cifrado ocupa más.
    Strip automático al guardar y al leer para evitar espacios ocultos.
    """
    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        decrypted = decrypt_value(value)
        # Strip al leer: elimina espacios aunque hayan quedado cifrados
        if isinstance(decrypted, str):
            return decrypted.strip() or None
        return decrypted

    def get_prep_value(self, value):
        if value is None or value == '':
            return None
        # Strip ANTES de cifrar: garantiza que nunca se guarda un espacio
        clean = str(value).strip()
        if not clean:
            return None
        return encrypt_value(clean)
