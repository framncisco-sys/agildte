/**
 * Departamentos y municipios de El Salvador (códigos 2 dígitos).
 * Fuente: Catálogo CAT-013 del Ministerio de Hacienda (MH).
 * Los municipios se identifican por zona (Norte, Centro, Sur, Este, Oeste, Costa).
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

/** Municipios por departamento según CAT-013 MH. */
export const MUNICIPIOS_POR_DEPARTAMENTO = {
  // Ahuachapán
  '01': [
    { codigo: '13', nombre: 'Ahuachapán Norte' },
    { codigo: '14', nombre: 'Ahuachapán Centro' },
    { codigo: '15', nombre: 'Ahuachapán Sur' },
  ],
  // Santa Ana
  '02': [
    { codigo: '14', nombre: 'Santa Ana Norte' },
    { codigo: '15', nombre: 'Santa Ana Centro' },
    { codigo: '16', nombre: 'Santa Ana Este' },
    { codigo: '17', nombre: 'Santa Ana Oeste' },
  ],
  // Sonsonate
  '03': [
    { codigo: '17', nombre: 'Sonsonate Norte' },
    { codigo: '18', nombre: 'Sonsonate Centro' },
    { codigo: '19', nombre: 'Sonsonate Este' },
    { codigo: '20', nombre: 'Sonsonate Oeste' },
  ],
  // Chalatenango
  '04': [
    { codigo: '34', nombre: 'Chalatenango Norte' },
    { codigo: '35', nombre: 'Chalatenango Centro' },
    { codigo: '36', nombre: 'Chalatenango Sur' },
  ],
  // La Libertad
  '05': [
    { codigo: '23', nombre: 'La Libertad Norte' },
    { codigo: '24', nombre: 'La Libertad Centro' },
    { codigo: '25', nombre: 'La Libertad Oeste' },
    { codigo: '26', nombre: 'La Libertad Este' },
    { codigo: '27', nombre: 'La Libertad Costa' },
    { codigo: '28', nombre: 'La Libertad Sur' },
  ],
  // San Salvador
  '06': [
    { codigo: '20', nombre: 'San Salvador Norte' },
    { codigo: '21', nombre: 'San Salvador Oeste' },
    { codigo: '22', nombre: 'San Salvador Este' },
    { codigo: '23', nombre: 'San Salvador Centro' },
    { codigo: '24', nombre: 'San Salvador Sur' },
  ],
  // Cuscatlán
  '07': [
    { codigo: '17', nombre: 'Cuscatlán Norte' },
    { codigo: '18', nombre: 'Cuscatlán Sur' },
  ],
  // La Paz
  '08': [
    { codigo: '23', nombre: 'La Paz Oeste' },
    { codigo: '24', nombre: 'La Paz Centro' },
    { codigo: '25', nombre: 'La Paz Este' },
  ],
  // Cabañas
  '09': [
    { codigo: '10', nombre: 'Cabañas Oeste' },
    { codigo: '11', nombre: 'Cabañas Este' },
  ],
  // San Vicente
  '10': [
    { codigo: '14', nombre: 'San Vicente Norte' },
    { codigo: '15', nombre: 'San Vicente Sur' },
  ],
  // Usulután
  '11': [
    { codigo: '24', nombre: 'Usulután Norte' },
    { codigo: '25', nombre: 'Usulután Este' },
    { codigo: '26', nombre: 'Usulután Oeste' },
  ],
  // Morazán
  '12': [
    { codigo: '27', nombre: 'Morazán Norte' },
    { codigo: '28', nombre: 'Morazán Sur' },
  ],
  // San Miguel
  '13': [
    { codigo: '21', nombre: 'San Miguel Norte' },
    { codigo: '22', nombre: 'San Miguel Centro' },
    { codigo: '23', nombre: 'San Miguel Oeste' },
  ],
  // La Unión
  '14': [
    { codigo: '19', nombre: 'La Unión Norte' },
    { codigo: '20', nombre: 'La Unión Sur' },
  ],
}
