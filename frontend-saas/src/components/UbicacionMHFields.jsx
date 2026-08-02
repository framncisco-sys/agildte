import { DEPARTAMENTOS, MUNICIPIOS_POR_DEPARTAMENTO } from '../data/departamentos-municipios'
import { getDistritos, distritoDefault } from '../data/distritos-cat008'

/**
 * Campos de ubicación MH V2: departamento + municipio (CAT-013) + distrito (CAT-008) + complemento.
 * Obligatorios para emisor/receptor en schemas fe-*-v2/v4.
 */
export function UbicacionMHFields({
  departamento,
  municipio,
  distrito,
  complemento,
  onChange,
  errors = {},
  required = true,
  showHint = true,
  namePrefix = '',
  className = '',
}) {
  const munis = MUNICIPIOS_POR_DEPARTAMENTO[departamento] || []
  const distritos = getDistritos(departamento, municipio)

  const setField = (field, value) => {
    if (field === 'departamento') {
      const nextMunis = MUNICIPIOS_POR_DEPARTAMENTO[value] || []
      const nextMuni = nextMunis[0]?.codigo || ''
      const nextDist = distritoDefault(value, nextMuni) || ''
      onChange({
        departamento: value,
        municipio: nextMuni,
        distrito: nextDist,
      })
      return
    }
    if (field === 'municipio') {
      const nextDist = distritoDefault(departamento, value) || ''
      onChange({ municipio: value, distrito: nextDist })
      return
    }
    onChange({ [field]: value })
  }

  const labelReq = required ? ' *' : ''
  const inputCls = (err) =>
    `w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
      err ? 'border-red-500' : 'border-gray-300'
    }`

  return (
    <div className={`space-y-3 ${className}`}>
      {showHint && (
        <p className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
          Normativa MH 2.0: la dirección usa <strong>municipio nuevo</strong> (códigos CAT-013) y{' '}
          <strong>distrito</strong> (antiguo municipio, CAT-008). Ejemplo San Salvador Centro:{' '}
          depto 06 → municipio 23 → distrito 14. Ejemplo San Miguel Centro:{' '}
          12 → 22 → 17. Ejemplo La Unión Norte: 14 → 19 → 16.
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Departamento{labelReq}
          </label>
          <select
            name={`${namePrefix}departamento`}
            value={departamento || ''}
            required={required}
            onChange={(e) => setField('departamento', e.target.value)}
            className={inputCls(errors.departamento)}
          >
            <option value="">Seleccione…</option>
            {DEPARTAMENTOS.map((d) => (
              <option key={d.codigo} value={d.codigo}>
                {d.nombre}
              </option>
            ))}
          </select>
          {errors.departamento && (
            <p className="mt-1 text-sm text-red-600">{errors.departamento}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Municipio (CAT-013){labelReq}
          </label>
          <select
            name={`${namePrefix}municipio`}
            value={municipio || ''}
            required={required}
            disabled={!departamento}
            onChange={(e) => setField('municipio', e.target.value)}
            className={inputCls(errors.municipio)}
          >
            <option value="">Seleccione…</option>
            {munis.map((m) => (
              <option key={m.codigo} value={m.codigo}>
                {m.nombre}
              </option>
            ))}
          </select>
          {errors.municipio && <p className="mt-1 text-sm text-red-600">{errors.municipio}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Distrito (CAT-008){labelReq}
          </label>
          <select
            name={`${namePrefix}distrito`}
            value={distrito || ''}
            required={required}
            disabled={!municipio || distritos.length === 0}
            onChange={(e) => setField('distrito', e.target.value)}
            className={inputCls(errors.distrito)}
          >
            <option value="">Seleccione…</option>
            {distritos.map((d) => (
              <option key={d.codigo} value={d.codigo}>
                {d.nombre}
              </option>
            ))}
          </select>
          {errors.distrito && <p className="mt-1 text-sm text-red-600">{errors.distrito}</p>}
        </div>
      </div>
      {complemento !== undefined && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Dirección / complemento{labelReq}
          </label>
          <input
            type="text"
            name={`${namePrefix}complemento`}
            value={complemento || ''}
            required={required}
            maxLength={200}
            onChange={(e) => setField('complemento', e.target.value)}
            placeholder="Colonia, calle, número, referencia…"
            className={inputCls(errors.complemento || errors.direccion)}
          />
          {(errors.complemento || errors.direccion) && (
            <p className="mt-1 text-sm text-red-600">{errors.complemento || errors.direccion}</p>
          )}
        </div>
      )}
    </div>
  )
}
