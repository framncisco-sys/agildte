/**
 * CAT-008 Distritos por departamento + municipio (CAT-013, códigos MH DTE).
 * Key: departamento (2 dig) -> municipio MH (2 dig) -> [{ codigo, nombre }]
 * Codigos de distrito = antiguos codigos de municipio MH.
 *
 * San Salvador: mapeo confirmado (Ciudad Delgado = 05).
 * Resto: catálogo MH/CNR legacy por departamento (orden oficial).
 */

function pad2(value) {
  const digitos = String(value ?? '').replace(/\D/g, '')
  if (!digitos) return ''
  return digitos.padStart(2, '0').slice(-2)
}

/** Etiquetas de municipios (CAT-013, códigos MH DTE). */
export const MUNI_LABELS = {
  '01': {
    '13': 'Ahuachapán Norte',
    '14': 'Ahuachapán Centro',
    '15': 'Ahuachapán Sur',
  },
  '02': {
    '14': 'Santa Ana Norte',
    '15': 'Santa Ana Centro',
    '16': 'Santa Ana Este',
    '17': 'Santa Ana Oeste',
  },
  '03': {
    '17': 'Sonsonate Norte',
    '18': 'Sonsonate Centro',
    '19': 'Sonsonate Este',
    '20': 'Sonsonate Oeste',
  },
  '04': {
    '34': 'Chalatenango Norte',
    '35': 'Chalatenango Centro',
    '36': 'Chalatenango Sur',
  },
  '05': {
    '23': 'La Libertad Norte',
    '24': 'La Libertad Centro',
    '25': 'La Libertad Oeste',
    '26': 'La Libertad Este',
    '27': 'La Libertad Costa',
    '28': 'La Libertad Sur',
  },
  '06': {
    '20': 'San Salvador Norte',
    '21': 'San Salvador Oeste',
    '22': 'San Salvador Este',
    '23': 'San Salvador Centro',
    '24': 'San Salvador Sur',
  },
  '07': {
    '17': 'Cuscatlán Norte',
    '18': 'Cuscatlán Sur',
  },
  '08': {
    '23': 'La Paz Oeste',
    '24': 'La Paz Centro',
    '25': 'La Paz Este',
  },
  '09': {
    '10': 'Cabañas Oeste',
    '11': 'Cabañas Este',
  },
  '10': {
    '14': 'San Vicente Norte',
    '15': 'San Vicente Sur',
  },
  '11': {
    '24': 'Usulután Norte',
    '25': 'Usulután Este',
    '26': 'Usulután Oeste',
  },
  '12': {
    '21': 'San Miguel Norte',
    '22': 'San Miguel Centro',
    '23': 'San Miguel Oeste',
  },
  '13': {
    '27': 'Morazán Norte',
    '28': 'Morazán Sur',
  },
  '14': {
    '19': 'La Unión Norte',
    '20': 'La Unión Sur',
  },
}

/** Cabecera conocida por municipio MH (departamento/municipio → código distrito). */
const DISTRITO_CABECERA = {
  '01/14': '01', // Ahuachapán
  '01/13': '03', // Atiquizaya
  '01/15': '08', // San Francisco Menéndez
  '02/15': '10', // Santa Ana
  '02/16': '02', // Coatepeque
  '02/14': '07', // Metapán
  '02/17': '03', // Chalchuapa
  '03/18': '15', // Sonsonate
  '03/19': '06', // Izalco
  '03/17': '07', // Juayúa
  '03/20': '01', // Acajutla
  '04/35': '16', // Nueva Concepción
  '04/34': '12', // La Palma
  '04/36': '07', // Chalatenango
  '05/24': '15', // San Juan Opico
  '05/27': '09', // La Libertad
  '05/26': '01', // Antiguo Cuscatlán
  '05/23': '12', // Quezaltepeque
  '05/25': '03', // Colón
  '05/28': '11', // Santa Tecla
  '06/23': '14', // San Salvador
  '06/22': '18', // Soyapango
  '06/20': '01', // Aguilares
  '06/21': '02', // Apopa
  '06/24': '13', // San Marcos
  '07/17': '15', // Suchitoto
  '07/18': '02', // Cojutepeque
  '08/24': '16', // San Pedro Nonualco
  '08/25': '21', // Zacatecoluca
  '08/23': '05', // Olocuilta
  '09/11': '06', // Sensuntepeque
  '09/10': '03', // Ilobasco
  '10/14': '01', // Apastepeque
  '10/15': '10', // San Vicente
  '11/25': '23', // Usulután
  '11/24': '21', // Santiago de María
  '11/26': '08', // Jiquilisco
  '12/22': '17', // San Miguel
  '12/21': '02', // Ciudad Barrios
  '12/23': '05', // Chinameca
  '13/27': '16', // Perquín
  '13/28': '19', // San Francisco Gotera
  '14/19': '16', // Santa Rosa de Lima
  '14/20': '08', // La Unión
}

export const DISTRITOS_POR_MUNICIPIO = {
  // ─── 01 Ahuachapán ───
  '01': {
    '14': [
      { codigo: '01', nombre: 'Ahuachapán' },
      { codigo: '02', nombre: 'Apaneca' },
      { codigo: '04', nombre: 'Concepción de Ataco' },
      { codigo: '11', nombre: 'Tacuba' },
    ],
    '13': [
      { codigo: '03', nombre: 'Atiquizaya' },
      { codigo: '05', nombre: 'El Refugio' },
      { codigo: '09', nombre: 'San Lorenzo' },
      { codigo: '12', nombre: 'Turín' },
    ],
    '15': [
      { codigo: '06', nombre: 'Guaymango' },
      { codigo: '07', nombre: 'Jujutla' },
      { codigo: '08', nombre: 'San Francisco Menéndez' },
      { codigo: '10', nombre: 'San Pedro Puxtla' },
    ],
  },

  // ─── 02 Santa Ana ───
  '02': {
    '15': [
      { codigo: '10', nombre: 'Santa Ana' },
    ],
    '16': [
      { codigo: '02', nombre: 'Coatepeque' },
      { codigo: '04', nombre: 'El Congo' },
    ],
    '14': [
      { codigo: '06', nombre: 'Masahuat' },
      { codigo: '07', nombre: 'Metapán' },
      { codigo: '11', nombre: 'Santa Rosa Guachipilín' },
      { codigo: '13', nombre: 'Texistepeque' },
    ],
    '17': [
      { codigo: '01', nombre: 'Candelaria de la Frontera' },
      { codigo: '03', nombre: 'Chalchuapa' },
      { codigo: '05', nombre: 'El Porvenir' },
      { codigo: '08', nombre: 'San Antonio Pajonal' },
      { codigo: '09', nombre: 'San Sebastián Salitrillo' },
      { codigo: '12', nombre: 'Santiago de la Frontera' },
    ],
  },

  // ─── 03 Sonsonate ───
  '03': {
    '18': [
      { codigo: '09', nombre: 'Nahulingo' },
      { codigo: '11', nombre: 'San Antonio del Monte' },
      { codigo: '14', nombre: 'Santo Domingo de Guzmán' },
      { codigo: '15', nombre: 'Sonsonate' },
      { codigo: '16', nombre: 'Sonzacate' },
    ],
    '19': [
      { codigo: '02', nombre: 'Armenia' },
      { codigo: '03', nombre: 'Caluco' },
      { codigo: '04', nombre: 'Cuisnahuat' },
      { codigo: '05', nombre: 'Santa Isabel Ishuatán' },
      { codigo: '06', nombre: 'Izalco' },
      { codigo: '12', nombre: 'San Julián' },
    ],
    '17': [
      { codigo: '07', nombre: 'Juayúa' },
      { codigo: '08', nombre: 'Nahuizalco' },
      { codigo: '10', nombre: 'Salcoatitán' },
      { codigo: '13', nombre: 'Santa Catarina Masahuat' },
    ],
    '20': [
      { codigo: '01', nombre: 'Acajutla' },
    ],
  },

  // ─── 04 Chalatenango ───
  '04': {
    '35': [
      { codigo: '01', nombre: 'Agua Caliente' },
      { codigo: '08', nombre: 'Dulce Nombre de María' },
      { codigo: '10', nombre: 'El Paraíso' },
      { codigo: '13', nombre: 'La Reina' },
      { codigo: '16', nombre: 'Nueva Concepción' },
      { codigo: '22', nombre: 'San Fernando' },
      { codigo: '24', nombre: 'San Francisco Morazán' },
      { codigo: '31', nombre: 'San Rafael' },
      { codigo: '32', nombre: 'Santa Rita' },
      { codigo: '33', nombre: 'Tejutla' },
    ],
    '34': [
      { codigo: '04', nombre: 'Citalá' },
      { codigo: '12', nombre: 'La Palma' },
      { codigo: '25', nombre: 'San Ignacio' },
    ],
    '36': [
      { codigo: '02', nombre: 'Arcatao' },
      { codigo: '03', nombre: 'Azacualpa' },
      { codigo: '05', nombre: 'Comalapa' },
      { codigo: '06', nombre: 'Concepción Quezaltepeque' },
      { codigo: '07', nombre: 'Chalatenango' },
      { codigo: '09', nombre: 'El Carrizal' },
      { codigo: '11', nombre: 'La Laguna' },
      { codigo: '14', nombre: 'Las Vueltas' },
      { codigo: '15', nombre: 'Nombre de Jesús' },
      { codigo: '17', nombre: 'Nueva Trinidad' },
      { codigo: '18', nombre: 'Ojos de Agua' },
      { codigo: '19', nombre: 'Potonico' },
      { codigo: '20', nombre: 'San Antonio de la Cruz' },
      { codigo: '21', nombre: 'San Antonio Los Ranchos' },
      { codigo: '23', nombre: 'San Francisco Lempa' },
      { codigo: '26', nombre: 'San Isidro Labrador' },
      { codigo: '27', nombre: 'San José Cancasque' },
      { codigo: '28', nombre: 'San José Las Flores' },
      { codigo: '29', nombre: 'San Luis del Carmen' },
      { codigo: '30', nombre: 'San Miguel de Mercedes' },
    ],
  },

  // ─── 05 La Libertad ───
  '05': {
    '24': [
      { codigo: '02', nombre: 'Ciudad Arce' },
      { codigo: '15', nombre: 'San Juan Opico' },
    ],
    '27': [
      { codigo: '05', nombre: 'Chiltiupán' },
      { codigo: '08', nombre: 'Jicalapa' },
      { codigo: '09', nombre: 'La Libertad' },
      { codigo: '18', nombre: 'Tamanique' },
      { codigo: '20', nombre: 'Teotepeque' },
    ],
    '26': [
      { codigo: '01', nombre: 'Antiguo Cuscatlán' },
      { codigo: '06', nombre: 'Huizúcar' },
      { codigo: '10', nombre: 'Nuevo Cuscatlán' },
      { codigo: '14', nombre: 'San José Villanueva' },
      { codigo: '22', nombre: 'Zaragoza' },
    ],
    '23': [
      { codigo: '12', nombre: 'Quezaltepeque' },
      { codigo: '16', nombre: 'San Matías' },
      { codigo: '17', nombre: 'San Pablo Tacachico' },
    ],
    '25': [
      { codigo: '03', nombre: 'Colón' },
      { codigo: '07', nombre: 'Jayaque' },
      { codigo: '13', nombre: 'Sacacoyo' },
      { codigo: '19', nombre: 'Talnique' },
      { codigo: '21', nombre: 'Tepecoyo' },
    ],
    '28': [
      { codigo: '04', nombre: 'Comasagua' },
      { codigo: '11', nombre: 'Santa Tecla' },
    ],
  },

  // ─── 06 San Salvador (mapeo confirmado) ───
  '06': {
    '23': [
      { codigo: '03', nombre: 'Ayutuxtepeque' },
      { codigo: '04', nombre: 'Cuscatancingo' },
      { codigo: '05', nombre: 'Ciudad Delgado' },
      { codigo: '09', nombre: 'Mejicanos' },
      { codigo: '14', nombre: 'San Salvador' },
    ],
    '22': [
      { codigo: '08', nombre: 'Ilopango' },
      { codigo: '15', nombre: 'San Martín' },
      { codigo: '18', nombre: 'Soyapango' },
      { codigo: '19', nombre: 'Tonacatepeque' },
    ],
    '20': [
      { codigo: '01', nombre: 'Aguilares' },
      { codigo: '06', nombre: 'El Paisnal' },
      { codigo: '07', nombre: 'Guazapa' },
    ],
    '21': [
      { codigo: '02', nombre: 'Apopa' },
      { codigo: '10', nombre: 'Nejapa' },
    ],
    '24': [
      { codigo: '11', nombre: 'Panchimalco' },
      { codigo: '12', nombre: 'Rosario de Mora' },
      { codigo: '13', nombre: 'San Marcos' },
      { codigo: '16', nombre: 'Santiago Texacuangos' },
      { codigo: '17', nombre: 'Santo Tomás' },
    ],
  },

  // ─── 07 Cuscatlán ───
  '07': {
    '17': [
      { codigo: '06', nombre: 'Oratorio de Concepción' },
      { codigo: '07', nombre: 'San Bartolomé Perulapía' },
      { codigo: '09', nombre: 'San José Guayabal' },
      { codigo: '10', nombre: 'San Pedro Perulapán' },
      { codigo: '15', nombre: 'Suchitoto' },
    ],
    '18': [
      { codigo: '01', nombre: 'Candelaria' },
      { codigo: '02', nombre: 'Cojutepeque' },
      { codigo: '03', nombre: 'El Carmen' },
      { codigo: '04', nombre: 'El Rosario' },
      { codigo: '05', nombre: 'Monte San Juan' },
      { codigo: '08', nombre: 'San Cristóbal' },
      { codigo: '11', nombre: 'San Rafael Cedros' },
      { codigo: '12', nombre: 'San Ramón' },
      { codigo: '13', nombre: 'Santa Cruz Analquito' },
      { codigo: '14', nombre: 'Santa Cruz Michapa' },
      { codigo: '16', nombre: 'Tenancingo' },
    ],
  },

  // ─── 08 La Paz ───
  '08': {
    '24': [
      { codigo: '02', nombre: 'El Rosario' },
      { codigo: '03', nombre: 'Jerusalén' },
      { codigo: '04', nombre: 'Mercedes La Ceiba' },
      { codigo: '06', nombre: 'Paraíso de Osorio' },
      { codigo: '07', nombre: 'San Antonio Masahuat' },
      { codigo: '08', nombre: 'San Emigdio' },
      { codigo: '12', nombre: 'San Juan Tepezontes' },
      { codigo: '14', nombre: 'San Miguel Tepezontes' },
      { codigo: '16', nombre: 'San Pedro Nonualco' },
      { codigo: '18', nombre: 'Santa María Ostuma' },
      { codigo: '19', nombre: 'Santiago Nonualco' },
      { codigo: '22', nombre: 'San Luis La Herradura' },
    ],
    '25': [
      { codigo: '10', nombre: 'San Juan Nonualco' },
      { codigo: '17', nombre: 'San Rafael Obrajuelo' },
      { codigo: '21', nombre: 'Zacatecoluca' },
    ],
    '23': [
      { codigo: '01', nombre: 'Cuyultitán' },
      { codigo: '05', nombre: 'Olocuilta' },
      { codigo: '09', nombre: 'San Francisco Chinameca' },
      { codigo: '11', nombre: 'San Juan Talpa' },
      { codigo: '13', nombre: 'San Luis Talpa' },
      { codigo: '15', nombre: 'San Pedro Masahuat' },
      { codigo: '20', nombre: 'Tapalhuaca' },
    ],
  },

  // ─── 09 Cabañas ───
  '09': {
    '11': [
      { codigo: '02', nombre: 'Guacotecti' },
      { codigo: '05', nombre: 'San Isidro' },
      { codigo: '06', nombre: 'Sensuntepeque' },
      { codigo: '08', nombre: 'Victoria' },
      { codigo: '09', nombre: 'Dolores' },
    ],
    '10': [
      { codigo: '01', nombre: 'Cinquera' },
      { codigo: '03', nombre: 'Ilobasco' },
      { codigo: '04', nombre: 'Jutiapa' },
      { codigo: '07', nombre: 'Tejutepeque' },
    ],
  },

  // ─── 10 San Vicente ───
  '10': {
    '14': [
      { codigo: '01', nombre: 'Apastepeque' },
      { codigo: '04', nombre: 'Santa Clara' },
      { codigo: '05', nombre: 'Santo Domingo' },
      { codigo: '06', nombre: 'San Esteban Catarina' },
      { codigo: '07', nombre: 'San Ildefonso' },
      { codigo: '08', nombre: 'San Lorenzo' },
      { codigo: '09', nombre: 'San Sebastián' },
    ],
    '15': [
      { codigo: '02', nombre: 'Guadalupe' },
      { codigo: '03', nombre: 'San Cayetano Istepeque' },
      { codigo: '10', nombre: 'San Vicente' },
      { codigo: '11', nombre: 'Tecoluca' },
      { codigo: '12', nombre: 'Tepetitán' },
      { codigo: '13', nombre: 'Verapaz' },
    ],
  },

  // ─── 11 Usulután ───
  '11': {
    '25': [
      { codigo: '03', nombre: 'California' },
      { codigo: '04', nombre: 'Concepción Batres' },
      { codigo: '06', nombre: 'Ereguayquín' },
      { codigo: '10', nombre: 'Jucuarán' },
      { codigo: '13', nombre: 'Ozatlán' },
      { codigo: '17', nombre: 'San Dionisio' },
      { codigo: '18', nombre: 'Santa Elena' },
      { codigo: '20', nombre: 'Santa María' },
      { codigo: '22', nombre: 'Tecapán' },
      { codigo: '23', nombre: 'Usulután' },
    ],
    '24': [
      { codigo: '01', nombre: 'Alegría' },
      { codigo: '02', nombre: 'Berlín' },
      { codigo: '05', nombre: 'El Triunfo' },
      { codigo: '07', nombre: 'Estanzuelas' },
      { codigo: '09', nombre: 'Jucuapa' },
      { codigo: '11', nombre: 'Mercedes Umaña' },
      { codigo: '12', nombre: 'Nueva Granada' },
      { codigo: '16', nombre: 'San Buenaventura' },
      { codigo: '21', nombre: 'Santiago de María' },
    ],
    '26': [
      { codigo: '08', nombre: 'Jiquilisco' },
      { codigo: '14', nombre: 'Puerto El Triunfo' },
      { codigo: '15', nombre: 'San Agustín' },
      { codigo: '19', nombre: 'San Francisco Javier' },
    ],
  },

  // ─── 12 San Miguel (CAT-012 oficial) ───
  '12': {
    '22': [
      { codigo: '03', nombre: 'Comacarán' },
      { codigo: '06', nombre: 'Chirilagua' },
      { codigo: '09', nombre: 'Moncagua' },
      { codigo: '12', nombre: 'Quelepa' },
      { codigo: '17', nombre: 'San Miguel' },
      { codigo: '20', nombre: 'Uluazapa' },
    ],
    '21': [
      { codigo: '01', nombre: 'Carolina' },
      { codigo: '02', nombre: 'Ciudad Barrios' },
      { codigo: '04', nombre: 'Chapeltique' },
      { codigo: '11', nombre: 'Nuevo Edén de San Juan' },
      { codigo: '13', nombre: 'San Antonio del Mosco' },
      { codigo: '14', nombre: 'San Gerardo' },
      { codigo: '16', nombre: 'San Luis de la Reina' },
      { codigo: '19', nombre: 'Sesori' },
    ],
    '23': [
      { codigo: '05', nombre: 'Chinameca' },
      { codigo: '07', nombre: 'El Tránsito' },
      { codigo: '08', nombre: 'Lolotique' },
      { codigo: '10', nombre: 'Nueva Guadalupe' },
      { codigo: '15', nombre: 'San Jorge' },
      { codigo: '18', nombre: 'San Rafael Oriente' },
    ],
  },

  // ─── 13 Morazán (CAT-012 oficial) ───
  '13': {
    '27': [
      { codigo: '01', nombre: 'Arambala' },
      { codigo: '02', nombre: 'Cacaopera' },
      { codigo: '03', nombre: 'Corinto' },
      { codigo: '07', nombre: 'El Rosario' },
      { codigo: '10', nombre: 'Joateca' },
      { codigo: '11', nombre: 'Jocoaitique' },
      { codigo: '14', nombre: 'Meanguera' },
      { codigo: '16', nombre: 'Perquín' },
      { codigo: '18', nombre: 'San Fernando' },
      { codigo: '20', nombre: 'San Isidro' },
      { codigo: '24', nombre: 'Torola' },
    ],
    '28': [
      { codigo: '04', nombre: 'Chilanga' },
      { codigo: '05', nombre: 'Delicias de Concepción' },
      { codigo: '06', nombre: 'El Divisadero' },
      { codigo: '08', nombre: 'Gualococti' },
      { codigo: '09', nombre: 'Guatajiagua' },
      { codigo: '12', nombre: 'Jocoro' },
      { codigo: '13', nombre: 'Lolotiquillo' },
      { codigo: '15', nombre: 'Osicala' },
      { codigo: '17', nombre: 'San Carlos' },
      { codigo: '19', nombre: 'San Francisco Gotera' },
      { codigo: '21', nombre: 'San Simón' },
      { codigo: '22', nombre: 'Sensembra' },
      { codigo: '23', nombre: 'Sociedad' },
      { codigo: '25', nombre: 'Yamabal' },
      { codigo: '26', nombre: 'Yoloaiquín' },
    ],
  },

  // ─── 14 La Unión ───
  '14': {
    '19': [
      { codigo: '01', nombre: 'Anamorós' },
      { codigo: '02', nombre: 'Bolívar' },
      { codigo: '03', nombre: 'Concepción de Oriente' },
      { codigo: '06', nombre: 'El Sauce' },
      { codigo: '09', nombre: 'Lislique' },
      { codigo: '11', nombre: 'Nueva Esparta' },
      { codigo: '12', nombre: 'Pasaquina' },
      { codigo: '13', nombre: 'Polorós' },
      { codigo: '15', nombre: 'San José' },
      { codigo: '16', nombre: 'Santa Rosa de Lima' },
    ],
    '20': [
      { codigo: '04', nombre: 'Conchagua' },
      { codigo: '05', nombre: 'El Carmen' },
      { codigo: '07', nombre: 'Intipucá' },
      { codigo: '08', nombre: 'La Unión' },
      { codigo: '10', nombre: 'Meanguera del Golfo' },
      { codigo: '14', nombre: 'San Alejo' },
      { codigo: '17', nombre: 'Yayantique' },
      { codigo: '18', nombre: 'Yucuaiquín' },
    ],
  },
}

/**
 * Distritos CAT-008 de un municipio (CAT-013 / códigos MH DTE).
 * @param {string|number} departamento Código departamento (2 dígitos)
 * @param {string|number} municipio Código municipio MH (2 dígitos)
 * @returns {{ codigo: string, nombre: string }[]}
 */
export function getDistritos(departamento, municipio) {
  const depto = pad2(departamento)
  const muni = pad2(municipio)
  if (!depto || !muni) return []
  return DISTRITOS_POR_MUNICIPIO[depto]?.[muni] ?? []
}

/**
 * Código de distrito por defecto (cabecera conocida o primer ítem).
 * @param {string|number} departamento
 * @param {string|number} municipio
 * @returns {string|null}
 */
export function distritoDefault(departamento, municipio) {
  const depto = pad2(departamento)
  const muni = pad2(municipio)
  if (!depto || !muni) return null
  const cabecera = DISTRITO_CABECERA[`${depto}/${muni}`]
  if (cabecera) return cabecera
  const lista = getDistritos(depto, muni)
  return lista[0]?.codigo ?? null
}

/**
 * Nombre del municipio CAT-013 (código MH DTE).
 * @param {string|number} departamento
 * @param {string|number} municipio
 * @returns {string|null}
 */
export function getMunicipioLabel(departamento, municipio) {
  const depto = pad2(departamento)
  const muni = pad2(municipio)
  return MUNI_LABELS[depto]?.[muni] ?? null
}
