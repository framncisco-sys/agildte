# Programador: Oscar Amaya Romero
"""Utilidades para integración Ministerio de Hacienda (MH) — El Salvador."""


def check_mh_online(timeout: int = 3) -> bool:
    """Verifica si el servidor MH (Hacienda El Salvador) responde."""
    import urllib.request
    import ssl

    url = "https://portaldgii.mh.gob.sv"
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, method="HEAD")
        urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return True
    except Exception:
        try:
            urllib.request.urlopen(url, timeout=timeout, context=ssl.create_default_context())
            return True
        except Exception:
            return False


CAUSAS_CONTINGENCIA = {
    1: "Falla en sistema de Hacienda (MH no responde)",
    2: "Falla de Internet",
    3: "Falla de Energía Eléctrica",
    4: "Falla en sistema local",
}
