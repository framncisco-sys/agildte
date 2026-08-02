"""Nombres de municipio (CAT-013) y distrito (CAT-008) para PDF / UI."""
import json
from functools import lru_cache
from pathlib import Path

from api.utils.mh_direccion import MUNI_CGEOES_A_MH

DEPARTAMENTOS = {
    '01': 'Ahuachapán', '02': 'Santa Ana', '03': 'Sonsonate', '04': 'Chalatenango',
    '05': 'La Libertad', '06': 'San Salvador', '07': 'Cuscatlán', '08': 'La Paz',
    '09': 'Cabañas', '10': 'San Vicente', '11': 'Usulután', '12': 'Morazán',
    '13': 'San Miguel', '14': 'La Unión',
}


@lru_cache(maxsize=1)
def _labels():
    path = Path(__file__).resolve().parent / 'mh_ubicacion_labels.json'
    return json.loads(path.read_text(encoding='utf-8'))


def _pad(codigo, default=''):
    raw = str(codigo or '').strip()
    digitos = ''.join(c for c in raw if c.isdigit())
    if not digitos:
        return default
    return digitos.zfill(2)[-2:]


def nombre_departamento(codigo):
    return DEPARTAMENTOS.get(_pad(codigo), '')


def municipio_mh_codigo(departamento, municipio):
    depto = _pad(departamento)
    muni = _pad(municipio)
    return MUNI_CGEOES_A_MH.get(depto, {}).get(muni, muni)


def nombre_municipio(departamento, municipio):
    depto = _pad(departamento)
    muni = municipio_mh_codigo(depto, municipio)
    return (_labels().get('municipios') or {}).get(depto, {}).get(muni, '')


def nombre_distrito(departamento, municipio, distrito):
    depto = _pad(departamento)
    muni = municipio_mh_codigo(depto, municipio)
    dist = _pad(distrito)
    if not (depto and muni and dist):
        return ''
    return (_labels().get('distritos') or {}).get(f'{depto}/{muni}/{dist}', '')


def armar_partes_ubicacion(complemento, departamento, municipio=None, distrito=None):
    """Partes legibles: complemento, distrito, municipio, departamento (solo no vacíos)."""
    partes = []
    comp = (complemento or '').strip().rstrip(',')
    if comp:
        partes.append(comp)
    dist_nom = nombre_distrito(departamento, municipio, distrito)
    if dist_nom:
        partes.append(f'Distrito {dist_nom}')
    muni_nom = nombre_municipio(departamento, municipio)
    if muni_nom:
        partes.append(muni_nom)
    depto_nom = nombre_departamento(departamento)
    if depto_nom:
        partes.append(depto_nom.upper())
    return partes
