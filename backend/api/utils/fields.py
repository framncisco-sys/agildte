"""
Campos personalizados para Django (cifrado, etc.).
"""
from django.db import models

from .encryption import decrypt_value, encrypt_value


class EncryptedTextField(models.TextField):
    """
    TextField que cifra el valor antes de guardar y descifra al leer.
    Compatible con datos legacy en texto plano (si el descifrado falla, devuelve el valor original).
    """
    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return decrypt_value(value)

    def get_prep_value(self, value):
        if value is None or value == '':
            return None
        return encrypt_value(str(value))


class EncryptedCharField(models.CharField):
    """
    CharField que cifra el valor antes de guardar y descifra al leer.
    Usar max_length generoso (ej: 500) porque el base64 cifrado ocupa más.
    """
    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return decrypt_value(value)

    def get_prep_value(self, value):
        if value is None or value == '':
            return None
        return encrypt_value(str(value))
