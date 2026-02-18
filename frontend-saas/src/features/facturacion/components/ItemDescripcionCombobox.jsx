import { useState, useEffect, useRef } from 'react'
import { searchItems } from '../../../api/items'

/**
 * Combobox/autocomplete para buscar ítems del catálogo y seleccionar uno.
 * Al seleccionar, llama onSelectItem({ descripcion, precio_unitario }).
 */
export function ItemDescripcionCombobox({
  value,
  onChange,
  onSelectItem,
  empresaId,
  placeholder = 'Buscar o escribir descripción...',
  className = '',
  inputClassName = '',
  error,
}) {
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const debounceRef = useRef(null)
  const wrapperRef = useRef(null)

  useEffect(() => {
    if (!value || value.length < 2 || !empresaId) {
      setSuggestions([])
      setOpen(false)
      return
    }
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setLoading(true)
      searchItems({ empresa_id: empresaId, q: value })
        .then((data) => {
          setSuggestions(Array.isArray(data) ? data : [])
          setOpen(true)
          setHighlightIndex(-1)
        })
        .catch(() => {
          setSuggestions([])
          setOpen(false)
        })
        .finally(() => setLoading(false))
    }, 250)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [value, empresaId])

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (item) => {
    onSelectItem({
      descripcion: item.descripcion ?? '',
      precio_unitario: Number(item.precio_unitario) ?? 0,
    })
    setOpen(false)
    setSuggestions([])
  }

  const handleKeyDown = (e) => {
    if (!open || suggestions.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightIndex((i) => (i < suggestions.length - 1 ? i + 1 : i))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightIndex((i) => (i > 0 ? i - 1 : -1))
    } else if (e.key === 'Enter' && highlightIndex >= 0 && suggestions[highlightIndex]) {
      e.preventDefault()
      handleSelect(suggestions[highlightIndex])
    } else if (e.key === 'Escape') {
      setOpen(false)
      setHighlightIndex(-1)
    }
  }

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => value && value.length >= 2 && suggestions.length > 0 && setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={`w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${inputClassName}`}
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={open}
      />
      {loading && (
        <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">...</span>
      )}
      {error && (
        <p className="text-xs text-red-600 mt-0.5">{error}</p>
      )}
      {open && suggestions.length > 0 && (
        <ul
          className="absolute z-20 left-0 right-0 mt-1 py-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-40 sm:max-h-48 overflow-y-auto"
          role="listbox"
        >
          {suggestions.map((item, i) => (
            <li
              key={item.id}
              role="option"
              aria-selected={i === highlightIndex}
              className={`px-3 py-2 text-sm cursor-pointer flex justify-between items-center ${
                i === highlightIndex ? 'bg-blue-50 text-blue-800' : 'hover:bg-gray-50'
              }`}
              onMouseDown={(e) => {
                e.preventDefault()
                handleSelect(item)
              }}
            >
              <span className="truncate">{item.descripcion}</span>
              <span className="text-gray-500 shrink-0 ml-2">
                ${Number(item.precio_unitario).toFixed(2)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
