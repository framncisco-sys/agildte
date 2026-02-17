import { useState } from 'react'
import { FileText, Receipt, CreditCard, FileMinus, UserX, Shield } from 'lucide-react'

const TIPOS_DOCUMENTO = [
  { codigo: '01', titulo: 'Factura', subtitulo: 'DTE-01', icono: FileText, color: 'border-blue-200 bg-blue-50 hover:border-blue-400', requiereDocRel: false },
  { codigo: '03', titulo: 'Crédito Fiscal', subtitulo: 'DTE-03', icono: Receipt, color: 'border-emerald-200 bg-emerald-50 hover:border-emerald-400', requiereDocRel: false },
  { codigo: '05', titulo: 'Nota de Crédito', subtitulo: 'DTE-05', icono: CreditCard, color: 'border-amber-200 bg-amber-50 hover:border-amber-400 ring-amber-400', requiereDocRel: true },
  { codigo: '06', titulo: 'Nota de Débito', subtitulo: 'DTE-06', icono: FileMinus, color: 'border-orange-200 bg-orange-50 hover:border-orange-400 ring-orange-400', requiereDocRel: true },
  { codigo: '14', titulo: 'Sujeto Excluido', subtitulo: 'DTE-14', icono: UserX, color: 'border-slate-200 bg-slate-50 hover:border-slate-400', requiereDocRel: false },
  { codigo: '07', titulo: 'Retención', subtitulo: 'DTE-07', icono: Shield, color: 'border-violet-200 bg-violet-50 hover:border-violet-400', requiereDocRel: false },
]

export function SelectorDocumento({ onSelect }) {
  const [seleccionado, setSeleccionado] = useState(null)

  const handleSelect = (codigo) => {
    setSeleccionado(codigo)
    onSelect(codigo)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-xl font-semibold text-gray-800 mb-6">Nueva Factura</h1>
      <p className="text-gray-600 mb-6">Selecciona el tipo de documento a emitir</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
        {TIPOS_DOCUMENTO.map(({ codigo, titulo, subtitulo, icono: Icono, color, requiereDocRel }) => {
          const estaSeleccionado = seleccionado === codigo
          const esDelicado = requiereDocRel && estaSeleccionado
          return (
            <button
              key={codigo}
              type="button"
              onClick={() => handleSelect(codigo)}
              className={`flex flex-col sm:flex-row items-center sm:items-start gap-3 p-4 sm:p-5 rounded-xl border-2 transition-all hover:scale-[1.02] ${color} ${esDelicado ? 'ring-2 ring-amber-500 border-amber-400' : ''}`}
            >
              <div className="p-2.5 rounded-lg bg-white/80 shadow-sm shrink-0">
                <Icono size={28} className="text-gray-700" />
              </div>
              <div className="text-center sm:text-left min-w-0">
                <p className="font-semibold text-gray-800 text-sm sm:text-base">{titulo}</p>
                <p className="text-xs text-gray-500">{subtitulo}</p>
                {requiereDocRel && (
                  <span className="inline-block mt-1 text-xs text-amber-700 font-medium">Requiere doc. relacionado</span>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
