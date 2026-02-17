/**
 * Departamentos y municipios de El Salvador (códigos 2 dígitos).
 * Fuente: Códigos estándar MH / Catálogo territorial.
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
  { codigo: '12', nombre: 'Morazán' },
  { codigo: '13', nombre: 'San Miguel' },
  { codigo: '14', nombre: 'La Unión' },
]

/** Municipios por departamento (principales). */
export const MUNICIPIOS_POR_DEPARTAMENTO = {
  '01': [
    { codigo: '01', nombre: 'Ahuachapán' },
    { codigo: '02', nombre: 'Apaneca' },
    { codigo: '03', nombre: 'Atiquizaya' },
  ],
  '02': [
    { codigo: '01', nombre: 'Santa Ana' },
    { codigo: '02', nombre: 'Chalchuapa' },
    { codigo: '03', nombre: 'Metapán' },
  ],
  '03': [
    { codigo: '01', nombre: 'Sonsonate' },
    { codigo: '02', nombre: 'Acajutla' },
    { codigo: '03', nombre: 'Izalco' },
  ],
  '04': [
    { codigo: '01', nombre: 'Chalatenango' },
    { codigo: '02', nombre: 'La Palma' },
    { codigo: '03', nombre: 'Nueva Concepción' },
  ],
  '05': [
    { codigo: '01', nombre: 'Santa Tecla' },
    { codigo: '02', nombre: 'La Libertad' },
    { codigo: '03', nombre: 'Zaragoza' },
    { codigo: '04', nombre: 'Antiguo Cuscatlán' },
  ],
  '06': [
    { codigo: '01', nombre: 'San Salvador' },
    { codigo: '02', nombre: 'Soyapango' },
    { codigo: '03', nombre: 'Mejicanos' },
    { codigo: '14', nombre: 'San Salvador (capital)' },
  ],
  '07': [
    { codigo: '01', nombre: 'Cojutepeque' },
    { codigo: '02', nombre: 'Suchitoto' },
  ],
  '08': [
    { codigo: '01', nombre: 'Zacatecoluca' },
    { codigo: '02', nombre: 'Olocuilta' },
    { codigo: '03', nombre: 'San Pedro Masahuat' },
  ],
  '09': [
    { codigo: '01', nombre: 'Sensuntepeque' },
    { codigo: '02', nombre: 'Ilobasco' },
  ],
  '10': [
    { codigo: '01', nombre: 'San Vicente' },
    { codigo: '02', nombre: 'Tecoluca' },
  ],
  '11': [
    { codigo: '01', nombre: 'Usulután' },
    { codigo: '02', nombre: 'Santiago de María' },
    { codigo: '03', nombre: 'Jucuapa' },
  ],
  '12': [
    { codigo: '01', nombre: 'San Francisco Gotera' },
    { codigo: '02', nombre: 'Perquín' },
  ],
  '13': [
    { codigo: '01', nombre: 'San Miguel' },
    { codigo: '02', nombre: 'Chinameca' },
    { codigo: '03', nombre: 'Usulután' },
  ],
  '14': [
    { codigo: '01', nombre: 'La Unión' },
    { codigo: '02', nombre: 'Santa Rosa de Lima' },
    { codigo: '03', nombre: 'Conchagua' },
  ],
}
