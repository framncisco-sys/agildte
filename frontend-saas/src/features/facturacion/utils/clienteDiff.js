import { DEPARTAMENTOS, MUNICIPIOS_POR_DEPARTAMENTO } from '../../../data/departamentos-municipios'
import { getDistritos } from '../../../data/distritos-cat008'

function norm(value) {
  return String(value ?? '').trim()
}

function normCode(value) {
  const digitos = String(value ?? '').replace(/\D/g, '')
  if (!digitos) return ''
  return digitos.padStart(2, '0').slice(-2)
}

function labelDepto(codigo) {
  const c = normCode(codigo)
  return DEPARTAMENTOS.find((d) => d.codigo === c)?.nombre || c || '(vacío)'
}

function labelMuni(depto, codigo) {
  const d = normCode(depto)
  const c = normCode(codigo)
  const lista = MUNICIPIOS_POR_DEPARTAMENTO[d] || []
  return lista.find((m) => m.codigo === c)?.nombre || c || '(vacío)'
}

function labelDist(depto, muni, codigo) {
  const c = normCode(codigo)
  const lista = getDistritos(normCode(depto), normCode(muni)) || []
  return lista.find((x) => x.codigo === c)?.nombre || c || '(vacío)'
}

/** Campos de ficha cliente comparables con el formulario de facturación. */
export const CAMPOS_CLIENTE_SYNC = [
  { form: 'nombreCompleto', label: 'Nombre' },
  { form: 'nombreComercial', label: 'Nombre comercial' },
  { form: 'tipoDocCliente', label: 'Tipo de documento' },
  { form: 'numeroDocumento', label: 'Número de documento' },
  { form: 'nrc', label: 'NRC' },
  { form: 'codActividad', label: 'Código de actividad' },
  { form: 'descActividad', label: 'Actividad económica' },
  { form: 'correo', label: 'Correo' },
  { form: 'telefono', label: 'Teléfono' },
  { form: 'departamento', label: 'Departamento', kind: 'depto' },
  { form: 'municipio', label: 'Municipio', kind: 'muni' },
  { form: 'distrito', label: 'Distrito', kind: 'dist' },
  { form: 'direccion', label: 'Dirección / complemento' },
]

/**
 * Snapshot de ficha desde el objeto Cliente de la API.
 */
export function snapshotDesdeCliente(cliente) {
  if (!cliente) return null
  const nitCliente = norm(cliente.nit || cliente.documento_identidad)
  const duiCliente = norm(cliente.dui)
  const tipoDoc = duiCliente && !nitCliente ? 'DUI' : 'NIT'
  const numeroDoc = tipoDoc === 'NIT' ? nitCliente : duiCliente
  return {
    nombreCompleto: norm(cliente.nombre),
    nombreComercial: norm(cliente.nombre_comercial || cliente.giro),
    tipoDocCliente: tipoDoc,
    numeroDocumento: numeroDoc,
    nrc: norm(cliente.nrc),
    codActividad: norm(cliente.cod_actividad || cliente.actividad_economica),
    descActividad: norm(cliente.desc_actividad),
    correo: norm(cliente.email_contacto || cliente.correo),
    telefono: norm(cliente.telefono),
    departamento: normCode(cliente.departamento || cliente.direccion_departamento),
    municipio: normCode(cliente.municipio || cliente.direccion_municipio),
    distrito: normCode(cliente.distrito || cliente.direccion_distrito),
    direccion: norm(cliente.direccion || cliente.direccion_complemento),
  }
}

function formatValor(campo, snapshotOrForm, value) {
  const raw = norm(value)
  if (!raw) return '(vacío)'
  if (campo.kind === 'depto') return labelDepto(raw)
  if (campo.kind === 'muni') {
    return labelMuni(snapshotOrForm.departamento, raw)
  }
  if (campo.kind === 'dist') {
    return labelDist(snapshotOrForm.departamento, snapshotOrForm.municipio, raw)
  }
  return raw
}

function valorComparable(campo, data) {
  const v = data?.[campo.form]
  if (campo.kind === 'depto' || campo.kind === 'muni' || campo.kind === 'dist') {
    return normCode(v)
  }
  if (campo.form === 'numeroDocumento' || campo.form === 'nrc' || campo.form === 'telefono') {
    return norm(v).replace(/\D/g, '') || norm(v)
  }
  return norm(v)
}

/**
 * Diffs entre snapshot de ficha y valores actuales del formulario.
 * @returns {{ campo: string, label: string, anterior: string, nuevo: string }[]}
 */
export function detectarCambiosCliente(snapshot, formData) {
  if (!snapshot || !formData) return []
  const formNorm = {
    ...formData,
    departamento: normCode(formData.departamento),
    municipio: normCode(formData.municipio),
    distrito: normCode(formData.distrito || formData.municipio),
  }
  const cambios = []
  for (const campo of CAMPOS_CLIENTE_SYNC) {
    const antes = valorComparable(campo, snapshot)
    const despues = valorComparable(campo, formNorm)
    if (antes === despues) continue
    cambios.push({
      campo: campo.form,
      label: campo.label,
      anterior: formatValor(campo, snapshot, snapshot[campo.form]),
      nuevo: formatValor(campo, formNorm, formNorm[campo.form]),
    })
  }
  return cambios
}
