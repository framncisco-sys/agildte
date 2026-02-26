import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SelectorDocumento } from '../components/SelectorDocumento'
import { FormularioFacturacion } from '../components/FormularioFacturacion'
import { obtenerPlantilla } from '../../../api/plantillas'

export function NuevaFactura() {
  const [tipoDocumento, setTipoDocumento] = useState(null)
  const [plantillaSeleccionada, setPlantillaSeleccionada] = useState(null)
  const [searchParams] = useSearchParams()
  const plantillaId = searchParams.get('plantillaId')

  useEffect(() => {
    let cancelado = false
    const cargarPlantilla = async () => {
      if (!plantillaId) {
        setPlantillaSeleccionada(null)
        return
      }
      try {
        const data = await obtenerPlantilla(plantillaId)
        if (cancelado) return
        setPlantillaSeleccionada(data)
        const tipo = (data.tipo_dte || '01').toString()
        setTipoDocumento(tipo)
      } catch {
        if (!cancelado) {
          setPlantillaSeleccionada(null)
        }
      }
    }
    // Solo cargar automáticamente si aún no se ha seleccionado tipo manualmente
    if (!tipoDocumento) {
      cargarPlantilla()
    }
    return () => {
      cancelado = true
    }
  }, [plantillaId, tipoDocumento])

  if (tipoDocumento === null) {
    return (
      <SelectorDocumento onSelect={(tipo) => setTipoDocumento(tipo)} />
    )
  }

  return (
    <FormularioFacturacion
      tipoDocumento={tipoDocumento}
      onChangeTipo={() => {
        setTipoDocumento(null)
        setPlantillaSeleccionada(null)
      }}
      plantillaSeleccionada={plantillaSeleccionada}
    />
  )
}
