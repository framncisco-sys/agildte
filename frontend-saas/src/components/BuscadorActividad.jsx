import { useState, useEffect, useRef } from 'react'
import { getActividades } from '../api/actividades'

const MIN_CHARS = 2
const DEBOUNCE_MS = 300

/**
 * Autocomplete de Actividad Económica (MH).
 * Al escribir 2+ caracteres consulta /api/actividades/?search=term.
 * Al seleccionar una opción, el input muestra "Código - Descripción" y notifica al padre con onChange(codigo).
 */
export function BuscadorActividad({
  value = '',           // código seleccionado (ej. "45201")
  displayValue = '',    // texto a mostrar en el input (ej. "45201 - Reparación de vehículos...")
  onChange,
  onDisplayChange,
  placeholder = 'Buscar por código o descripción (mín. 2 caracteres)',
  disabled = false,
  className = '',
  error = false,
  id,
}) {
  const [inputText, setInputText] = useState(displayValue || '')
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [options, setOptions] = useState([])
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const containerRef = useRef(null)
  const debounceRef = useRef(null)

  useEffect(() => {
    setInputText(displayValue || '')
  }, [displayValue])

  useEffect(() => {
    if (inputText.length < MIN_CHARS) {
      setOptions([])
      setOpen(false)
      return
    }
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setLoading(true)
      getActividades({ search: inputText, limit: 20 })
        .then((data) => {
          const list = data.results || data || []
          setOptions(list)
          setOpen(list.length > 0)
          setHighlightIndex(-1)
        })
        .catch(() => {
          setOptions([])
          setOpen(false)
        })
        .finally(() => setLoading(false))
    }, DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [inputText])

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selectItem = (item) => {
    const codigo = item.codigo || item
    const desc = item.descripcion != null ? item.descripcion : (typeof item === 'string' ? item : '')
    const display = desc ? `${codigo} - ${desc}` : codigo
    setInputText(display)
    setOpen(false)
    setOptions([])
    onChange?.(codigo)
    onDisplayChange?.(display)
  }

  const handleInputChange = (e) => {
    const v = e.target.value
    setInputText(v)
    if (!v) {
      onChange?.('')
      onDisplayChange?.('')
    }
    if (v.length < MIN_CHARS) setOpen(false)
  }

  const handleKeyDown = (e) => {
    if (!open || options.length === 0) {
      if (e.key === 'Escape') setOpen(false)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightIndex((i) => (i < options.length - 1 ? i + 1 : 0))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightIndex((i) => (i > 0 ? i - 1 : options.length - 1))
      return
    }
    if (e.key === 'Enter' && highlightIndex >= 0 && options[highlightIndex]) {
      e.preventDefault()
      selectItem(options[highlightIndex])
      return
    }
    if (e.key === 'Escape') {
      setOpen(false)
      setHighlightIndex(-1)
    }
  }

  const inputCn = `w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${error ? 'border-red-500' : 'border-gray-300'} ${className}`

  return (
    <div ref={containerRef} className="relative">
      <input
        type="text"
        id={id}
        value={inputText}
        onChange={handleInputChange}
        onFocus={() => inputText.length >= MIN_CHARS && options.length > 0 && setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        className={inputCn}
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls="actividades-listbox"
        aria-activedescendant={highlightIndex >= 0 && options[highlightIndex] ? `actividad-opt-${options[highlightIndex].codigo}` : undefined}
      />
      {loading && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">Buscando...</span>
      )}
      {open && options.length > 0 && (
        <ul
          id="actividades-listbox"
          role="listbox"
          className="absolute z-[100] left-0 right-0 mt-1 py-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto"
        >
          {options.map((item, idx) => (
            <li
              key={item.codigo}
              id={`actividad-opt-${item.codigo}`}
              role="option"
              aria-selected={idx === highlightIndex}
              className={`px-3 py-2 text-sm cursor-pointer truncate ${idx === highlightIndex ? 'bg-blue-100 text-blue-900' : 'hover:bg-gray-100 text-gray-800'}`}
              onMouseEnter={() => setHighlightIndex(idx)}
              onClick={() => selectItem(item)}
            >
              {item.codigo} - {item.descripcion}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
