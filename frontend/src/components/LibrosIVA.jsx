import React, { useState, useEffect } from 'react';
import { usePeriodo } from '../contexts/PeriodoContext';

const LibrosIVA = ({ clienteInfo, volverAlInicio, onEditar }) => {
  const { mes, anio, periodoFormateado } = usePeriodo();
  const [tabActiva, setTabActiva] = useState('compras');
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [modoBorrar, setModoBorrar] = useState(false);
  const [seleccionados, setSeleccionados] = useState(new Set());
  const [eliminando, setEliminando] = useState(false);

  const empresaId = clienteInfo?.id;

  // Función para cargar vista previa
  const cargarVistaPrevia = async (tipo) => {
    if (!empresaId || !periodoFormateado) {
      setError('Falta empresa o período');
      return;
    }

    setCargando(true);
    setError(null);

    try {
      let url = '';
      if (tipo === 'compras') {
        url = `http://127.0.0.1:8000/api/libros-iva/vista-previa-compras/?empresa_id=${empresaId}&periodo=${periodoFormateado}`;
      } else if (tipo === 'ccf') {
        url = `http://127.0.0.1:8000/api/libros-iva/vista-previa-ventas-ccf/?empresa_id=${empresaId}&periodo=${periodoFormateado}`;
      } else if (tipo === 'cf') {
        url = `http://127.0.0.1:8000/api/libros-iva/vista-previa-ventas-cf/?empresa_id=${empresaId}&periodo=${periodoFormateado}`;
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      const json = await response.json();
      setDatos(json);
    } catch (err) {
      setError(err.message);
      setDatos(null);
    } finally {
      setCargando(false);
    }
  };

  // Cargar datos cuando cambia la tab activa o el período
  useEffect(() => {
    if (empresaId && periodoFormateado) {
      cargarVistaPrevia(tabActiva);
    }
  }, [tabActiva, periodoFormateado, empresaId]);

  // Función para descargar CSV
  const descargarCSV = (tipo) => {
    if (!empresaId || !periodoFormateado) {
      alert('Falta empresa o período');
      return;
    }

    let url = '';
    if (tipo === 'compras') {
      url = `http://127.0.0.1:8000/api/libros-iva/csv-compras/?empresa_id=${empresaId}&periodo=${periodoFormateado}`;
    } else if (tipo === 'ccf') {
      url = `http://127.0.0.1:8000/api/libros-iva/csv-ventas-ccf/?empresa_id=${empresaId}&periodo=${periodoFormateado}`;
    } else if (tipo === 'cf') {
      url = `http://127.0.0.1:8000/api/libros-iva/csv-ventas-cf/?empresa_id=${empresaId}&periodo=${periodoFormateado}`;
    }

    window.open(url, '_blank');
  };

  // Función para descargar PDF
  const descargarPDF = (tipo) => {
    if (!empresaId || !periodoFormateado) {
      alert('Falta empresa o período');
      return;
    }

    let url = '';
    if (tipo === 'compras') {
      url = `http://127.0.0.1:8000/api/libros-iva/pdf-compras/?empresa_id=${empresaId}&periodo=${periodoFormateado}`;
    } else if (tipo === 'ccf') {
      url = `http://127.0.0.1:8000/api/libros-iva/pdf-ventas-ccf/?empresa_id=${empresaId}&periodo=${periodoFormateado}`;
    } else if (tipo === 'cf') {
      url = `http://127.0.0.1:8000/api/libros-iva/pdf-ventas-cf/?empresa_id=${empresaId}&periodo=${periodoFormateado}`;
    }

    window.open(url, '_blank');
  };

  // Función para navegar a editar documento
  const editarDocumento = (id, tipo) => {
    if (modoBorrar) {
      // En modo borrar, toggle selección
      const nuevosSeleccionados = new Set(seleccionados);
      if (nuevosSeleccionados.has(id)) {
        nuevosSeleccionados.delete(id);
      } else {
        nuevosSeleccionados.add(id);
      }
      setSeleccionados(nuevosSeleccionados);
      return;
    }

    // Navegar a edición
    if (onEditar) {
      const tipoEdicion = tipo === 'compras' ? 'compra' : 'venta';
      onEditar(id, tipoEdicion);
    }
  };

  // Toggle seleccionar todo
  const toggleSeleccionarTodo = () => {
    if (!datos || !datos.datos) return;
    
    if (seleccionados.size === datos.datos.length) {
      setSeleccionados(new Set());
    } else {
      setSeleccionados(new Set(datos.datos.map(item => item.id)));
    }
  };

  // Eliminar seleccionados
  const eliminarSeleccionados = async () => {
    if (seleccionados.size === 0) {
      alert("No hay documentos seleccionados");
      return;
    }

    const confirmar = window.confirm(
      `¿Estás seguro de que deseas eliminar ${seleccionados.size} documento(s)?\n\nEsta acción no se puede deshacer.`
    );

    if (!confirmar) return;

    setEliminando(true);
    const ids = Array.from(seleccionados);
    const tipo = tabActiva === 'compras' ? 'compra' : 'venta';
    const endpoint = tipo === 'compra' ? 'compras' : 'ventas';

    try {
      // Eliminar en paralelo
      const promesas = ids.map(id => 
        fetch(`http://127.0.0.1:8000/api/${endpoint}/borrar/${id}/`, {
          method: 'DELETE'
        })
      );

      const resultados = await Promise.allSettled(promesas);
      const exitosos = resultados.filter(r => r.status === 'fulfilled' && r.value.ok).length;
      const fallidos = resultados.length - exitosos;

      if (exitosos > 0) {
        alert(`✅ ${exitosos} documento(s) eliminado(s) exitosamente${fallidos > 0 ? `\n⚠️ ${fallidos} documento(s) no se pudieron eliminar` : ''}`);
        // Recargar datos
        setSeleccionados(new Set());
        setModoBorrar(false);
        cargarVistaPrevia(tabActiva);
      } else {
        alert(`❌ No se pudo eliminar ningún documento`);
      }
    } catch (error) {
      console.error("Error eliminando:", error);
      alert("Error al eliminar documentos");
    } finally {
      setEliminando(false);
    }
  };

  const formatearMoneda = (valor) => {
    return new Intl.NumberFormat('es-SV', { style: 'currency', currency: 'USD' }).format(valor);
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ margin: 0, color: '#2c3e50' }}>📊 Libros de IVA y Reportes</h2>
          <p style={{ margin: '5px 0', color: '#7f8c8d' }}>
            {clienteInfo?.nombre} - Período: {periodoFormateado}
          </p>
        </div>
        <button
          onClick={volverAlInicio}
          style={{
            padding: '10px 20px',
            background: '#95a5a6',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            fontSize: '0.9em'
          }}
        >
          ← Volver al Dashboard
        </button>
      </div>

      {/* TABS */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '2px solid #ecf0f1' }}>
        {['compras', 'ccf', 'cf'].map((tab) => (
          <button
            key={tab}
            onClick={() => setTabActiva(tab)}
            style={{
              padding: '12px 24px',
              background: tabActiva === tab ? '#3498db' : 'transparent',
              color: tabActiva === tab ? 'white' : '#7f8c8d',
              border: 'none',
              borderBottom: tabActiva === tab ? '3px solid #2980b9' : '3px solid transparent',
              cursor: 'pointer',
              fontWeight: tabActiva === tab ? 'bold' : 'normal',
              fontSize: '1em',
              transition: '0.3s'
            }}
          >
            {tab === 'compras' && '🛍️ Compras'}
            {tab === 'ccf' && '💼 Ventas a Contribuyentes'}
            {tab === 'cf' && '🛒 Ventas a Consumidor Final'}
          </button>
        ))}
      </div>

      {/* BOTONES DE ACCIÓN */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <button
          onClick={() => cargarVistaPrevia(tabActiva)}
          disabled={cargando}
          style={{
            padding: '10px 20px',
            background: '#27ae60',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: cargando ? 'not-allowed' : 'pointer',
            fontSize: '0.9em'
          }}
        >
          {cargando ? '⏳ Cargando...' : '🔄 Actualizar Vista Previa'}
        </button>
        <button
          onClick={() => descargarPDF(tabActiva)}
          disabled={modoBorrar}
          style={{
            padding: '10px 20px',
            background: '#e74c3c',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: modoBorrar ? 'not-allowed' : 'pointer',
            fontSize: '0.9em',
            opacity: modoBorrar ? 0.5 : 1
          }}
        >
          📄 Descargar PDF
        </button>
        <button
          onClick={() => descargarCSV(tabActiva)}
          disabled={modoBorrar}
          style={{
            padding: '10px 20px',
            background: '#f39c12',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: modoBorrar ? 'not-allowed' : 'pointer',
            fontSize: '0.9em',
            opacity: modoBorrar ? 0.5 : 1
          }}
        >
          📊 Descargar CSV (MH)
        </button>
        
        {/* BOTÓN MODO BORRAR */}
        {!modoBorrar ? (
          <button
            onClick={() => {
              setModoBorrar(true);
              setSeleccionados(new Set());
            }}
            style={{
              padding: '10px 20px',
              background: '#95a5a6',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer',
              fontSize: '0.9em',
              marginLeft: 'auto'
            }}
          >
            🗑️ Modo Borrar
          </button>
        ) : (
          <>
            <button
              onClick={() => {
                setModoBorrar(false);
                setSeleccionados(new Set());
              }}
              style={{
                padding: '10px 20px',
                background: '#7f8c8d',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
                fontSize: '0.9em'
              }}
            >
              ✖️ Cancelar
            </button>
            <button
              onClick={eliminarSeleccionados}
              disabled={seleccionados.size === 0 || eliminando}
              style={{
                padding: '10px 20px',
                background: seleccionados.size > 0 ? '#c0392b' : '#95a5a6',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: seleccionados.size > 0 && !eliminando ? 'pointer' : 'not-allowed',
                fontSize: '0.9em',
                fontWeight: 'bold'
              }}
            >
              {eliminando ? '⏳ Eliminando...' : `🗑️ Eliminar Seleccionados (${seleccionados.size})`}
            </button>
          </>
        )}
      </div>

      {/* VISTA PREVIA */}
      {error && (
        <div style={{
          padding: '15px',
          background: '#fee',
          color: '#c0392b',
          borderRadius: '5px',
          marginBottom: '20px'
        }}>
          ⚠️ Error: {error}
        </div>
      )}

      {cargando && (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>⏳ Cargando datos...</p>
        </div>
      )}

      {!cargando && datos && (
        <div>
          {/* RESUMEN DE TOTALES */}
          <div style={{
            background: 'white',
            padding: '20px',
            borderRadius: '8px',
            boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
            marginBottom: '20px',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '15px'
          }}>
            <div>
              <p style={{ margin: 0, color: '#7f8c8d', fontSize: '0.9em' }}>Total Registros</p>
              <h3 style={{ margin: '5px 0', color: '#2c3e50' }}>{datos.total_registros}</h3>
            </div>
            <div>
              <p style={{ margin: 0, color: '#7f8c8d', fontSize: '0.9em' }}>Gravado</p>
              <h3 style={{ margin: '5px 0', color: '#27ae60' }}>{formatearMoneda(datos.totales.gravado)}</h3>
            </div>
            <div>
              <p style={{ margin: 0, color: '#7f8c8d', fontSize: '0.9em' }}>IVA</p>
              <h3 style={{ margin: '5px 0', color: '#3498db' }}>{formatearMoneda(datos.totales.iva)}</h3>
            </div>
            <div>
              <p style={{ margin: 0, color: '#7f8c8d', fontSize: '0.9em' }}>Total General</p>
              <h3 style={{ margin: '5px 0', color: '#e74c3c' }}>{formatearMoneda(datos.totales.total)}</h3>
            </div>
          </div>

          {/* TABLA DE DATOS */}
          <div style={{
            background: 'white',
            borderRadius: '8px',
            boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
            overflow: 'auto'
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#34495e', color: 'white' }}>
                  {modoBorrar && (
                    <th style={{ padding: '12px', textAlign: 'center', fontSize: '0.9em', width: '50px' }}>
                      <input
                        type="checkbox"
                        checked={datos && datos.datos && seleccionados.size === datos.datos.length && datos.datos.length > 0}
                        onChange={toggleSeleccionarTodo}
                        style={{ cursor: 'pointer' }}
                      />
                    </th>
                  )}
                  {tabActiva === 'compras' && (
                    <>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Fecha</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Tipo Doc</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Código</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>NRC Proveedor</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Proveedor</th>
                      <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Gravado</th>
                      <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>IVA</th>
                      <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Total</th>
                      <th style={{ padding: '12px', textAlign: 'center', fontSize: '0.9em' }}>Acción</th>
                    </>
                  )}
                  {tabActiva === 'ccf' && (
                    <>
                      {modoBorrar && <th></th>}
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Fecha</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Nº Documento</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Código</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Cliente</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>NRC</th>
                      <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Gravado</th>
                      <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>IVA</th>
                      <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Total</th>
                      <th style={{ padding: '12px', textAlign: 'center', fontSize: '0.9em' }}>Acción</th>
                    </>
                  )}
                  {tabActiva === 'cf' && (
                    <>
                      {modoBorrar && <th></th>}
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Fecha</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Nº Documento</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Código</th>
                      <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Nº Control</th>
                      <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Gravado</th>
                      <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>IVA</th>
                      <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Total</th>
                      <th style={{ padding: '12px', textAlign: 'center', fontSize: '0.9em' }}>Acción</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {datos.datos.length === 0 ? (
                  <tr>
                    <td colSpan={tabActiva === 'compras' ? (modoBorrar ? 10 : 9) : tabActiva === 'ccf' ? (modoBorrar ? 10 : 9) : (modoBorrar ? 9 : 8)} style={{ padding: '40px', textAlign: 'center', color: '#7f8c8d' }}>
                      No hay registros para este período
                    </td>
                  </tr>
                ) : (
                  datos.datos.map((item, index) => (
                    <tr
                      key={item.id || index}
                      style={{
                        borderBottom: '1px solid #ecf0f1',
                        cursor: 'pointer',
                        transition: '0.2s',
                        background: seleccionados.has(item.id) ? '#fff3cd' : 'white'
                      }}
                      onMouseEnter={(e) => {
                        if (!seleccionados.has(item.id)) {
                          e.currentTarget.style.background = '#f8f9fa';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!seleccionados.has(item.id)) {
                          e.currentTarget.style.background = 'white';
                        } else {
                          e.currentTarget.style.background = '#fff3cd';
                        }
                      }}
                      onClick={() => editarDocumento(item.id, tabActiva)}
                    >
                      {modoBorrar && (
                        <td style={{ padding: '10px', textAlign: 'center' }}>
                          <input
                            type="checkbox"
                            checked={seleccionados.has(item.id)}
                            onChange={() => editarDocumento(item.id, tabActiva)}
                            onClick={(e) => e.stopPropagation()}
                            style={{ cursor: 'pointer' }}
                          />
                        </td>
                      )}
                      {tabActiva === 'compras' && (
                        <>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.fecha_emision}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.tipo_documento}</td>
                          <td style={{ padding: '10px', fontSize: '0.85em', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.codigo_generacion || '-'}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.nrc_proveedor}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.nombre_proveedor}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.9em' }}>{formatearMoneda(item.monto_gravado)}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.9em' }}>{formatearMoneda(item.monto_iva)}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.9em', fontWeight: 'bold' }}>{formatearMoneda(item.monto_total)}</td>
                          {!modoBorrar && (
                            <td style={{ padding: '10px', textAlign: 'center' }}>
                              <span style={{ color: '#3498db', fontSize: '0.8em' }}>✏️ Editar</span>
                            </td>
                          )}
                        </>
                      )}
                      {tabActiva === 'ccf' && (
                        <>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.fecha_emision}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.numero_documento || '-'}</td>
                          <td style={{ padding: '10px', fontSize: '0.85em', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.codigo_generacion || '-'}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.nombre_receptor || '-'}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.nrc_receptor || '-'}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.9em' }}>{formatearMoneda(item.venta_gravada)}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.9em' }}>{formatearMoneda(item.debito_fiscal)}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.9em', fontWeight: 'bold' }}>{formatearMoneda(item.total)}</td>
                          {!modoBorrar && (
                            <td style={{ padding: '10px', textAlign: 'center' }}>
                              <span style={{ color: '#3498db', fontSize: '0.8em' }}>✏️ Editar</span>
                            </td>
                          )}
                        </>
                      )}
                      {tabActiva === 'cf' && (
                        <>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.fecha_emision}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.numero_documento || '-'}</td>
                          <td style={{ padding: '10px', fontSize: '0.85em', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.codigo_generacion || '-'}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em' }}>{item.numero_control || '-'}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.9em' }}>{formatearMoneda(item.venta_gravada)}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.9em' }}>{formatearMoneda(item.debito_fiscal)}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.9em', fontWeight: 'bold' }}>{formatearMoneda(item.total)}</td>
                          {!modoBorrar && (
                            <td style={{ padding: '10px', textAlign: 'center' }}>
                              <span style={{ color: '#3498db', fontSize: '0.8em' }}>✏️ Editar</span>
                            </td>
                          )}
                        </>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {!modoBorrar && (
            <p style={{ marginTop: '15px', color: '#7f8c8d', fontSize: '0.85em', textAlign: 'center' }}>
              💡 Haz clic en cualquier fila para editar el documento
            </p>
          )}
          {modoBorrar && (
            <p style={{ marginTop: '15px', color: '#c0392b', fontSize: '0.85em', textAlign: 'center', fontWeight: 'bold' }}>
              ⚠️ Modo Borrar: Selecciona los documentos que deseas eliminar
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default LibrosIVA;

