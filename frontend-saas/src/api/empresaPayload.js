/**
 * Prepara el payload de empresa para create/update (JSON o multipart).
 */
export function buildEmpresaPayload(form) {
  const payload = { ...form }

  delete payload.logo_url
  delete payload.certificado_nombre

  if (!payload.clave_api_mh) delete payload.clave_api_mh
  if (!payload.clave_certificado) delete payload.clave_certificado
  if (!payload.whatsapp_access_token) delete payload.whatsapp_access_token

  if (!(payload.logo instanceof File)) delete payload.logo
  if (!(payload.archivo_certificado instanceof File)) delete payload.archivo_certificado

  payload.whatsapp_premium_enabled = Boolean(payload.whatsapp_premium_enabled)
  payload.dashboard_compras_premium_enabled = Boolean(payload.dashboard_compras_premium_enabled)

  return payload
}

function appendFormFields(form, payload) {
  Object.keys(payload).forEach((k) => {
    const v = payload[k]
    if (v === undefined || v === null) return
    if (k === 'logo' || k === 'archivo_certificado') return
    if (typeof v === 'boolean') {
      form.append(k, v ? 'true' : 'false')
    } else {
      form.append(k, v)
    }
  })
  if (payload.logo instanceof File) form.append('logo', payload.logo)
  if (payload.archivo_certificado instanceof File) {
    form.append('archivo_certificado', payload.archivo_certificado)
  }
}

export function needsEmpresaMultipart(payload) {
  return payload.logo instanceof File || payload.archivo_certificado instanceof File
}

export function empresaPayloadToFormData(payload) {
  const form = new FormData()
  appendFormFields(form, payload)
  return form
}
