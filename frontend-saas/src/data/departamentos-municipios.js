/**
 * Departamentos y municipios MH (CAT-012 / CAT-013 v1.1).
 * Códigos de los 44 municipios nuevos usados en DTE (no confundir con CGEOES 01..N).
 * Fuente: catálogo MH / Contaportable normativa 2.0 (ej. San Salvador Centro = 23).
 */
export const DEPARTAMENTOS = [
  { codigo: '01', nombre: 'Ahuachapán' },
  { codigo: '02', nombre: 'Santa Ana' },
  { codigo: '03', nombre: 'Sonsonate' },
  { codigo: '04', nombre: 'Chalatenango' },
  { codigo: '05', nombre: 'La Libertad' },
  { codigo: '06', nombre: 'San Salvador' },
  { codigo: '07', nombre: 'Cuscatlán' },
  { codigo: '08', nombre: 'La Paz' },
  { codigo: '09', nombre: 'Cabañas' },
  { codigo: '10', nombre: 'San Vicente' },
  { codigo: '11', nombre: 'Usulután' },
  { codigo: '12', nombre: 'San Miguel' },
  { codigo: '13', nombre: 'Morazán' },
  { codigo: '14', nombre: 'La Unión' },
]

/** Municipios por departamento según CAT-013 MH (DTE). */
export const MUNICIPIOS_POR_DEPARTAMENTO = {
  '01': [
    { codigo: '13', nombre: 'Ahuachapán Norte' },
    { codigo: '14', nombre: 'Ahuachapán Centro' },
    { codigo: '15', nombre: 'Ahuachapán Sur' },
  ],
  '02': [
    { codigo: '14', nombre: 'Santa Ana Norte' },
    { codigo: '15', nombre: 'Santa Ana Centro' },
    { codigo: '16', nombre: 'Santa Ana Este' },
    { codigo: '17', nombre: 'Santa Ana Oeste' },
  ],
  '03': [
    { codigo: '17', nombre: 'Sonsonate Norte' },
    { codigo: '18', nombre: 'Sonsonate Centro' },
    { codigo: '19', nombre: 'Sonsonate Este' },
    { codigo: '20', nombre: 'Sonsonate Oeste' },
  ],
  '04': [
    { codigo: '34', nombre: 'Chalatenango Norte' },
    { codigo: '35', nombre: 'Chalatenango Centro' },
    { codigo: '36', nombre: 'Chalatenango Sur' },
  ],
  '05': [
    { codigo: '23', nombre: 'La Libertad Norte' },
    { codigo: '24', nombre: 'La Libertad Centro' },
    { codigo: '25', nombre: 'La Libertad Oeste' },
    { codigo: '26', nombre: 'La Libertad Este' },
    { codigo: '27', nombre: 'La Libertad Costa' },
    { codigo: '28', nombre: 'La Libertad Sur' },
  ],
  '06': [
    { codigo: '20', nombre: 'San Salvador Norte' },
    { codigo: '21', nombre: 'San Salvador Oeste' },
    { codigo: '22', nombre: 'San Salvador Este' },
    { codigo: '23', nombre: 'San Salvador Centro' },
    { codigo: '24', nombre: 'San Salvador Sur' },
  ],
  '07': [
    { codigo: '17', nombre: 'Cuscatlán Norte' },
    { codigo: '18', nombre: 'Cuscatlán Sur' },
  ],
  '08': [
    { codigo: '23', nombre: 'La Paz Oeste' },
    { codigo: '24', nombre: 'La Paz Centro' },
    { codigo: '25', nombre: 'La Paz Este' },
  ],
  '09': [
    { codigo: '10', nombre: 'Cabañas Oeste' },
    { codigo: '11', nombre: 'Cabañas Este' },
  ],
  '10': [
    { codigo: '14', nombre: 'San Vicente Norte' },
    { codigo: '15', nombre: 'San Vicente Sur' },
  ],
  '11': [
    { codigo: '24', nombre: 'Usulután Norte' },
    { codigo: '25', nombre: 'Usulután Este' },
    { codigo: '26', nombre: 'Usulután Oeste' },
  ],
  '12': [
    { codigo: '21', nombre: 'San Miguel Norte' },
    { codigo: '22', nombre: 'San Miguel Centro' },
    { codigo: '23', nombre: 'San Miguel Oeste' },
  ],
  '13': [
    { codigo: '27', nombre: 'Morazán Norte' },
    { codigo: '28', nombre: 'Morazán Sur' },
  ],
  '14': [
    { codigo: '19', nombre: 'La Unión Norte' },
    { codigo: '20', nombre: 'La Unión Sur' },
  ],
}

/** Si alguien guardó códigos CGEOES (01..N), mapear a CAT-013 MH DTE. */
export const MUNI_CGEOES_A_MH = {
  '01': { '01': '14', '02': '13', '03': '15' },
  '02': { '01': '15', '02': '16', '03': '14', '04': '17' },
  '03': { '01': '18', '02': '19', '03': '17', '04': '20' },
  '04': { '01': '35', '02': '34', '03': '36' },
  '05': { '01': '24', '02': '27', '03': '26', '04': '23', '05': '25', '06': '28' },
  '06': { '01': '23', '02': '22', '03': '20', '04': '21', '05': '24' },
  '07': { '01': '17', '02': '18' },
  '08': { '01': '24', '02': '25', '03': '23' },
  '09': { '01': '11', '02': '10' },
  '10': { '01': '14', '02': '15' },
  '11': { '01': '25', '02': '24', '03': '26' },
  '12': { '01': '22', '02': '21', '03': '23' },
  '13': { '01': '27', '02': '28' },
  '14': { '01': '19', '02': '20' },
}

export function municipioMh(departamento, municipio) {
  const d = String(departamento || '').padStart(2, '0').slice(-2)
  const m = String(municipio || '').padStart(2, '0').slice(-2)
  return MUNI_CGEOES_A_MH[d]?.[m] || m
}

function pad2(valor, def = '') {
  const digitos = String(valor ?? '').replace(/\D/g, '')
  if (!digitos) return def
  return digitos.padStart(2, '0').slice(-2)
}

/**
 * Normaliza ubicación para formularios DTE (CAT-012/013 oficial).
 * Corrige el swap histórico 12/13 (San Miguel↔Morazán) y códigos CGEOES 01..N.
 */
export function normalizarUbicacionMh(departamento, municipio, distrito) {
  let d = pad2(departamento, '06')
  const mRaw = pad2(municipio, '')
  let m = MUNI_CGEOES_A_MH[d]?.[mRaw] || mRaw

  // Municipios MH de San Miguel / Morazán fuerzan el depto CAT-012 correcto.
  if (['21', '22', '23'].includes(m)) d = '12'
  else if (['27', '28'].includes(m)) d = '13'
  else if (d === '13' && ['01', '02', '03'].includes(mRaw)) {
    // Histórico: San Miguel guardado como depto 13 + CGEOES
    d = '12'
    m = MUNI_CGEOES_A_MH['12']?.[mRaw] || m
  } else if (d === '12' && ['01', '02'].includes(mRaw) && !['21', '22', '23'].includes(m)) {
    d = '13'
    m = MUNI_CGEOES_A_MH['13']?.[mRaw] || m
  }

  if (!m || !MUNICIPIOS_POR_DEPARTAMENTO[d]?.some((x) => x.codigo === m)) {
    m = MUNICIPIOS_POR_DEPARTAMENTO[d]?.[0]?.codigo || '23'
  }

  let di = pad2(distrito, '')
  return { departamento: d, municipio: m, distrito: di }
}
