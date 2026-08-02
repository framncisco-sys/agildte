"""
Helpers de dirección JSON MH V2+ (fe-f-v2 / fe-ccf-v4).
Municipio = CAT-013 MH DTE (ej. San Salvador Centro=23, La Unión Norte=19).
Distrito = CAT-008 (antiguos municipios, ej. San Salvador=14, Santa Rosa=16).
No usar códigos CGEOES 01..N como municipio DTE.
"""

MUNICIPIOS_VALIDOS = {
    '01': {'13', '14', '15'},
    '02': {'14', '15', '16', '17'},
    '03': {'17', '18', '19', '20'},
    '04': {'34', '35', '36'},
    '05': {'23', '24', '25', '26', '27', '28'},
    '06': {'20', '21', '22', '23', '24'},
    '07': {'17', '18'},
    '08': {'23', '24', '25'},
    '09': {'10', '11'},
    '10': {'14', '15'},
    '11': {'24', '25', '26'},
    # CAT-012 oficial: 12=San Miguel, 13=Morazán
    '12': {'21', '22', '23'},
    '13': {'27', '28'},
    '14': {'19', '20'},
}

# Si BD tiene códigos CGEOES (01..N) por error → CAT-013 MH
MUNI_CGEOES_A_MH = {
    '01': {'01': '14', '02': '13', '03': '15'},
    '02': {'01': '15', '02': '16', '03': '14', '04': '17'},
    '03': {'01': '18', '02': '19', '03': '17', '04': '20'},
    '04': {'01': '35', '02': '34', '03': '36'},
    '05': {'01': '24', '02': '27', '03': '26', '04': '23', '05': '25', '06': '28'},
    '06': {'01': '23', '02': '22', '03': '20', '04': '21', '05': '24'},
    '07': {'01': '17', '02': '18'},
    '08': {'01': '24', '02': '25', '03': '23'},
    '09': {'01': '11', '02': '10'},
    '10': {'01': '14', '02': '15'},
    '11': {'01': '25', '02': '24', '03': '26'},
    '12': {'01': '22', '02': '21', '03': '23'},
    '13': {'01': '27', '02': '28'},
    '14': {'01': '19', '02': '20'},
}

MUNI_CABECERA = {
    '01': '14', '02': '15', '03': '18', '04': '35', '05': '24',
    '06': '23', '07': '18', '08': '24', '09': '10', '10': '15',
    '11': '25', '12': '22', '13': '28', '14': '19',
}

DISTRITO_POR_MUNI = {
    ('01', '13'): '03', ('01', '14'): '01', ('01', '15'): '08',
    ('02', '14'): '07', ('02', '15'): '10', ('02', '16'): '02', ('02', '17'): '03',
    ('03', '17'): '07', ('03', '18'): '15', ('03', '19'): '06', ('03', '20'): '01',
    ('04', '34'): '12', ('04', '35'): '16', ('04', '36'): '07',
    ('05', '23'): '12', ('05', '24'): '15', ('05', '25'): '03',
    ('05', '26'): '01', ('05', '27'): '09', ('05', '28'): '11',
    ('06', '20'): '01', ('06', '21'): '02', ('06', '22'): '18',
    ('06', '23'): '14', ('06', '24'): '13',
    ('07', '17'): '15', ('07', '18'): '02',
    ('08', '23'): '05', ('08', '24'): '16', ('08', '25'): '21',
    ('09', '10'): '03', ('09', '11'): '06',
    ('10', '14'): '01', ('10', '15'): '10',
    ('11', '24'): '21', ('11', '25'): '23', ('11', '26'): '08',
    ('12', '21'): '02', ('12', '22'): '17', ('12', '23'): '05',
    ('13', '27'): '16', ('13', '28'): '19',
    ('14', '19'): '16', ('14', '20'): '08',
}

DISTRITOS_VALIDOS = {
    ('06', '23'): {'03', '04', '05', '09', '14'},
    ('06', '20'): {'01', '06', '07'},
    ('06', '21'): {'02', '10'},
    ('06', '22'): {'08', '15', '18', '19'},
    ('06', '24'): {'11', '12', '13', '16', '17'},
    ('12', '22'): {'03', '06', '09', '12', '17', '20'},
    ('14', '19'): {'01', '02', '03', '06', '09', '11', '12', '13', '15', '16'},
    ('14', '20'): {'04', '05', '07', '08', '10', '14', '17', '18'},
    ('11', '26'): {'08', '14', '15', '19'},
    ('11', '24'): {'01', '02', '05', '07', '11', '12', '16', '21', '22'},
    ('11', '25'): {'03', '04', '06', '10', '13', '17', '18', '20', '23', '24'},
}

# Municipios que identifican San Miguel / Morazán aunque el depto esté invertido en BD.
_MUNI_SAN_MIGUEL = frozenset({'21', '22', '23'})
_MUNI_MORAZAN = frozenset({'27', '28'})


def codigo_ubicacion(valor, default='23'):
    raw = str(valor or '').strip()
    digitos = ''.join(c for c in raw if c.isdigit())
    if not digitos:
        return str(default).zfill(2)[:2]
    return digitos.zfill(2)[-2:]


def normalizar_ubicacion_mh(departamento, municipio, distrito=None):
    depto = codigo_ubicacion(departamento, '06')
    muni_raw = codigo_ubicacion(municipio, MUNI_CABECERA.get(depto, '23'))
    dist_in = None if distrito in (None, '') else codigo_ubicacion(distrito, '01')

    # Corregir CGEOES → MH DTE
    muni = MUNI_CGEOES_A_MH.get(depto, {}).get(muni_raw, muni_raw)

    # Corregir swap histórico 12/13 (UI tenía Morazán↔San Miguel invertidos vs CAT-012).
    if depto == '13' and muni in _MUNI_SAN_MIGUEL:
        depto = '12'
    elif depto == '12' and muni in _MUNI_MORAZAN:
        depto = '13'
    # Si quedó CGEOES bajo el depto invertido, reintentar mapa oficial.
    muni = MUNI_CGEOES_A_MH.get(depto, {}).get(muni_raw, muni)

    validos = MUNICIPIOS_VALIDOS.get(depto)
    if validos and muni not in validos:
        dist = dist_in or muni_raw
        muni = MUNI_CABECERA.get(depto, '23')
    else:
        dist = dist_in

    cabecera = DISTRITO_POR_MUNI.get((depto, muni)) or '01'
    permitidos = DISTRITOS_VALIDOS.get((depto, muni))
    if not dist or dist == muni or (permitidos and dist not in permitidos):
        dist = cabecera

    return depto, muni, dist


def armar_direccion_mh(departamento, municipio, complemento, distrito=None, default_depto='06', default_muni='23'):
    depto, muni, dist = normalizar_ubicacion_mh(
        departamento or default_depto,
        municipio or default_muni,
        distrito,
    )
    comp = (complemento or '').strip() or 'San Salvador'
    return {
        'departamento': depto,
        'municipio': muni,
        'distrito': dist,
        'complemento': comp[:200],
    }
