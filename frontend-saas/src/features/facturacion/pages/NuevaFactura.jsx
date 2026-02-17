import { useState } from 'react'
import { SelectorDocumento } from '../components/SelectorDocumento'
import { FormularioFacturacion } from '../components/FormularioFacturacion'

export function NuevaFactura() {
  const [tipoDocumento, setTipoDocumento] = useState(null)

  if (tipoDocumento === null) {
    return (
      <SelectorDocumento onSelect={(tipo) => setTipoDocumento(tipo)} />
    )
  }

  return (
    <FormularioFacturacion
      tipoDocumento={tipoDocumento}
      onChangeTipo={() => setTipoDocumento(null)}
    />
  )
}
