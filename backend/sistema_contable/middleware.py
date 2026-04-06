"""Middleware mínimo para rutas que deben responder sí o sí (evita 404 fantasma del router)."""

from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication


def _path_match(path: str) -> bool:
    p = (path or '').split('?')[0].rstrip('/') or '/'
    return p in (
        '/api/facturas/descarga-zip',
        '/api/descarga-zip',
        '/api/ventas/descargar-lote',
    )


class DescargaZipDirectMiddleware:
    """
    GET /api/facturas/descarga-zip/ y /api/descarga-zip/ → download_batch_ventas.

    Autentica JWT aquí: este middleware corre antes que las vistas DRF, así que hay que
    rellenar request.user igual que haría @api_view; si no, siempre salía 401 con sesión "abierta".
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._jwt = JWTAuthentication()

    def __call__(self, request):
        if request.method == 'GET' and (
            _path_match(request.path) or _path_match(request.META.get('PATH_INFO', ''))
        ):
            try:
                auth = self._jwt.authenticate(Request(request))
                if auth is not None:
                    request.user, request.auth = auth
            except Exception:
                # Sin token o token inválido: request.user sigue anónimo; la vista devuelve 401.
                pass
            from api.views import download_batch_ventas

            return download_batch_ventas(request)
        return self.get_response(request)
