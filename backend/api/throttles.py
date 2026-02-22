"""
Throttle classes personalizadas para endpoints críticos de AgilDTE.
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Límite de intentos de login por IP: 10 por minuto."""
    scope = 'login'


class DTERateThrottle(UserRateThrottle):
    """Límite de emisión/invalidación DTE por usuario: 60 por minuto."""
    scope = 'dte'
