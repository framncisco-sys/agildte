import React, { useState, useEffect } from 'react';
import { usePeriodo } from '../contexts/PeriodoContext';

const GestionRetenciones = ({ clienteInfo, volverAlInicio }) => {
  const { periodoFormateado } = usePeriodo();
  const [retenciones, setRetenciones] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');
  const [modalAbierto, setModalAbierto] = useState(false);
  const [retencionSeleccionada, setRetencionSeleccionada] = useState(null);
  const [ventasDisponibles, setVentasDisponibles] = useState([]);
  const [ventasSeleccionadas, setVentasSeleccionadas] = useState([]);
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [tipoDoc, setTipoDoc] = useState('CCF');
  const [justificacion, setJustificacion] = useState('');
  const [cargandoVentas, setCargandoVentas] = useState(false);
  const [validacionError, setValidacionError] = useState('');

  useEffect(() => {
    cargarRetenciones();
  }, [clienteInfo, periodoFormateado]);

  const cargarRetenciones = async () => {
    if (!clienteInfo?.id) return;
    
    setCargando(true);
    setError('');
    
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/retenciones-recibidas/listar/?empresa_id=${clienteInfo.id}&periodo=${periodoFormateado}`
      );
      
      if (!response.ok) {
        throw new Error('Error al cargar retenciones');
      }
      
      const data = await response.json();
      setRetenciones(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  const abrirModalConciliacion = (retencion) => {
    setRetencionSeleccionada(retencion);
    setModalAbierto(true);
    setVentasDisponibles([]);
    setVentasSeleccionadas([]);
    setFechaDesde('');
    setFechaHasta('');
    setTipoDoc('CCF');
    setJustificacion('');
    setValidacionError('');
    
    // Establecer fechas por defecto (últimos 3 meses)
    const hoy = new Date();
    const hace3Meses = new Date();
    hace3Meses.setMonth(hace3Meses.getMonth() - 3);
    
    setFechaDesde(hace3Meses.toISOString().split('T')[0]);
    setFechaHasta(hoy.toISOString().split('T')[0]);
  };

  const cerrarModal = () => {
    setModalAbierto(false);
    setRetencionSeleccionada(null);
    setVentasDisponibles([]);
    setVentasSeleccionadas([]);
    setValidacionError('');
    setJustificacion('');
  };

  const buscarVentas = async () => {
    if (!fechaDesde || !fechaHasta || !clienteInfo?.id) {
      alert('Debes seleccionar un rango de fechas');
      return;
    }

    setCargandoVentas(true);
    setValidacionError('');
    
    try {
      const url = `http://127.0.0.1:8000/api/ventas/para-conciliacion/?empresa_id=${clienteInfo.id}&fecha_desde=${fechaDesde}&fecha_hasta=${fechaHasta}&tipo_doc=${tipoDoc}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Error al cargar ventas');
      }
      
      const data = await response.json();
      setVentasDisponibles(data.ventas || []);
    } catch (err) {
      setValidacionError(err.message);
    } finally {
      setCargandoVentas(false);
    }
  };

  const toggleVentaSeleccionada = (ventaId) => {
    setVentasSeleccionadas(prev => {
      if (prev.includes(ventaId)) {
        return prev.filter(id => id !== ventaId);
      } else {
        return [...prev, ventaId];
      }
    });
    setValidacionError('');
  };

  const calcularSumaRetenciones = () => {
    const ventasSeleccionadasObj = ventasDisponibles.filter(v => ventasSeleccionadas.includes(v.id));
    return ventasSeleccionadasObj.reduce((sum, v) => sum + (v.retencion_calculada || 0), 0);
  };

  const aplicarRetencion = async () => {
    if (!retencionSeleccionada) return;
    
    if (ventasSeleccionadas.length === 0) {
      setValidacionError('Debes seleccionar al menos una venta');
      return;
    }

    const sumaRetenciones = calcularSumaRetenciones();
    const montoDisponible = parseFloat(retencionSeleccionada.monto_retenido_1 || 0);
    const diferencia = sumaRetenciones - montoDisponible;

    if (diferencia > 0.01) {
      if (!justificacion.trim()) {
        setValidacionError(`La suma de retenciones ($${sumaRetenciones.toFixed(2)}) excede el monto disponible ($${montoDisponible.toFixed(2)}). Debes proporcionar una justificación.`);
        return;
      }
    }

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/retenciones-recibidas/${retencionSeleccionada.id}/aplicar/`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            ventas_ids: ventasSeleccionadas,
            justificacion: justificacion || ''
          })
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Error al aplicar retención');
      }

      alert('✅ Retención aplicada correctamente');
      cerrarModal();
      cargarRetenciones(); // Recargar lista
    } catch (err) {
      setValidacionError(err.message);
    }
  };

  const descargarCSV162 = async () => {
    if (!clienteInfo?.id) {
      alert('No hay empresa seleccionada');
      return;
    }

    try {
      const url = `http://127.0.0.1:8000/api/reportes/csv-162/?empresa_id=${clienteInfo.id}&periodo=${periodoFormateado}`;
      window.open(url, '_blank');
    } catch (err) {
      alert('Error al descargar CSV 162: ' + err.message);
    }
  };

  const formatearFecha = (fecha) => {
    if (!fecha) return '';
    const d = new Date(fecha);
    return d.toLocaleDateString('es-SV');
  };

  const formatearMoneda = (valor) => {
    return new Intl.NumberFormat('es-SV', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(valor || 0);
  };

  const obtenerEstadoColor = (estado) => {
    return estado === 'Aplicada' ? '#27ae60' : '#f39c12';
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div>
          <h2 style={{ margin: 0, color: '#2c3e50' }}>📋 Gestión de Retenciones Recibidas</h2>
          <p style={{ color: '#7f8c8d', margin: '5px 0 0 0' }}>
            Período: <strong>{periodoFormateado}</strong> | Empresa: <strong>{clienteInfo?.nombre}</strong>
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={descargarCSV162}
            style={{
              padding: '10px 20px',
              background: '#27ae60',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            📥 Descargar CSV 162
          </button>
          <button
            onClick={volverAlInicio}
            style={{
              padding: '10px 20px',
              background: '#95a5a6',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            ← Volver
          </button>
        </div>
      </div>

      {/* ERROR */}
      {error && (
        <div style={{ padding: '15px', background: '#e74c3c', color: 'white', borderRadius: '5px', marginBottom: '20px' }}>
          ❌ {error}
        </div>
      )}

      {/* TABLA */}
      {cargando ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>Cargando retenciones...</p>
        </div>
      ) : retenciones.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', background: 'white', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
          <p style={{ color: '#7f8c8d', fontSize: '1.1em' }}>No hay retenciones registradas para este período.</p>
        </div>
      ) : (
        <div style={{ background: 'white', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#34495e', color: 'white' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>Fecha</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Agente</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>NIT Agente</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Monto Sujeto</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Retención 1%</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Estado</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Código Generación</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {retenciones.map((ret, index) => (
                <tr
                  key={ret.id || index}
                  style={{
                    borderBottom: '1px solid #ecf0f1',
                    background: index % 2 === 0 ? 'white' : '#f8f9fa'
                  }}
                >
                  <td style={{ padding: '12px' }}>{formatearFecha(ret.fecha_documento)}</td>
                  <td style={{ padding: '12px' }}>{ret.nombre_agente || '-'}</td>
                  <td style={{ padding: '12px' }}>{ret.nit_agente || '-'}</td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>
                    {formatearMoneda(ret.monto_sujeto)}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', color: '#27ae60' }}>
                    {formatearMoneda(ret.monto_retenido_1)}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <span
                      style={{
                        padding: '5px 10px',
                        borderRadius: '5px',
                        background: obtenerEstadoColor(ret.estado),
                        color: 'white',
                        fontSize: '0.85em',
                        fontWeight: 'bold'
                      }}
                    >
                      {ret.estado || 'Pendiente'}
                    </span>
                  </td>
                  <td style={{ padding: '12px', fontSize: '0.85em', color: '#7f8c8d' }}>
                    {ret.codigo_generacion ? ret.codigo_generacion.substring(0, 20) + '...' : '-'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {ret.estado === 'Pendiente' ? (
                      <button
                        onClick={() => abrirModalConciliacion(ret)}
                        style={{
                          padding: '6px 12px',
                          background: '#3498db',
                          color: 'white',
                          border: 'none',
                          borderRadius: '5px',
                          cursor: 'pointer',
                          fontSize: '0.85em'
                        }}
                      >
                        🔗 Conciliar
                      </button>
                    ) : (
                      <span style={{ color: '#7f8c8d', fontSize: '0.85em' }}>
                        {ret.ventas_aplicadas_detalle?.length || 0} venta(s)
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ background: '#ecf0f1', fontWeight: 'bold' }}>
                <td colSpan="3" style={{ padding: '12px', textAlign: 'right' }}>TOTALES:</td>
                <td style={{ padding: '12px', textAlign: 'right' }}>
                  {formatearMoneda(retenciones.reduce((sum, ret) => sum + parseFloat(ret.monto_sujeto || 0), 0))}
                </td>
                <td style={{ padding: '12px', textAlign: 'right', color: '#27ae60' }}>
                  {formatearMoneda(retenciones.reduce((sum, ret) => sum + parseFloat(ret.monto_retenido_1 || 0), 0))}
                </td>
                <td colSpan="3"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* MODAL DE CONCILIACIÓN */}
      {modalAbierto && retencionSeleccionada && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1000
          }}
          onClick={cerrarModal}
        >
          <div
            style={{
              background: 'white',
              borderRadius: '10px',
              padding: '30px',
              maxWidth: '900px',
              width: '90%',
              maxHeight: '90vh',
              overflow: 'auto',
              boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginTop: 0, color: '#2c3e50' }}>
              🔗 Conciliar Retención
            </h3>
            <p style={{ color: '#7f8c8d' }}>
              Retención de <strong>{retencionSeleccionada.nombre_agente}</strong> por{' '}
              <strong>{formatearMoneda(retencionSeleccionada.monto_retenido_1)}</strong>
            </p>

            {/* FILTROS */}
            <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '5px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: '10px', alignItems: 'end' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em', fontWeight: 'bold' }}>
                    Fecha Desde:
                  </label>
                  <input
                    type="date"
                    value={fechaDesde}
                    onChange={(e) => setFechaDesde(e.target.value)}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '3px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em', fontWeight: 'bold' }}>
                    Fecha Hasta:
                  </label>
                  <input
                    type="date"
                    value={fechaHasta}
                    onChange={(e) => setFechaHasta(e.target.value)}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '3px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em', fontWeight: 'bold' }}>
                    Tipo Doc:
                  </label>
                  <select
                    value={tipoDoc}
                    onChange={(e) => setTipoDoc(e.target.value)}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '3px' }}
                  >
                    <option value="CCF">CCF (Contribuyente)</option>
                    <option value="CF">CF (Consumidor Final)</option>
                  </select>
                </div>
                <button
                  onClick={buscarVentas}
                  disabled={cargandoVentas}
                  style={{
                    padding: '8px 15px',
                    background: '#3498db',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: cargandoVentas ? 'not-allowed' : 'pointer',
                    height: 'fit-content'
                  }}
                >
                  {cargandoVentas ? 'Buscando...' : '🔍 Buscar'}
                </button>
              </div>
            </div>

            {/* ERROR DE VALIDACIÓN */}
            {validacionError && (
              <div style={{ padding: '10px', background: '#e74c3c', color: 'white', borderRadius: '5px', marginBottom: '15px' }}>
                ⚠️ {validacionError}
              </div>
            )}

            {/* TABLA DE VENTAS */}
            {ventasDisponibles.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: '#2c3e50' }}>Ventas Disponibles:</h4>
                <div style={{ maxHeight: '300px', overflow: 'auto', border: '1px solid #ddd', borderRadius: '5px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead style={{ background: '#ecf0f1', position: 'sticky', top: 0 }}>
                      <tr>
                        <th style={{ padding: '10px', textAlign: 'left', fontSize: '0.85em' }}>Seleccionar</th>
                        <th style={{ padding: '10px', textAlign: 'left', fontSize: '0.85em' }}>Fecha</th>
                        <th style={{ padding: '10px', textAlign: 'left', fontSize: '0.85em' }}>Documento</th>
                        <th style={{ padding: '10px', textAlign: 'left', fontSize: '0.85em' }}>Cliente</th>
                        <th style={{ padding: '10px', textAlign: 'right', fontSize: '0.85em' }}>Venta Gravada</th>
                        <th style={{ padding: '10px', textAlign: 'right', fontSize: '0.85em' }}>Retención 1%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ventasDisponibles.map((venta) => (
                        <tr
                          key={venta.id}
                          style={{
                            borderBottom: '1px solid #ecf0f1',
                            background: ventasSeleccionadas.includes(venta.id) ? '#e8f5e9' : 'white'
                          }}
                        >
                          <td style={{ padding: '10px', textAlign: 'center' }}>
                            <input
                              type="checkbox"
                              checked={ventasSeleccionadas.includes(venta.id)}
                              onChange={() => toggleVentaSeleccionada(venta.id)}
                            />
                          </td>
                          <td style={{ padding: '10px', fontSize: '0.85em' }}>{formatearFecha(venta.fecha_emision)}</td>
                          <td style={{ padding: '10px', fontSize: '0.85em' }}>{venta.numero_documento || '-'}</td>
                          <td style={{ padding: '10px', fontSize: '0.85em' }}>{venta.nombre_receptor || '-'}</td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.85em' }}>
                            {formatearMoneda(venta.venta_gravada)}
                          </td>
                          <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.85em', fontWeight: 'bold' }}>
                            {formatearMoneda(venta.retencion_calculada)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* RESUMEN */}
            {ventasSeleccionadas.length > 0 && (
              <div style={{ marginBottom: '20px', padding: '15px', background: '#e8f5e9', borderRadius: '5px' }}>
                <p style={{ margin: '5px 0', fontWeight: 'bold' }}>
                  Ventas seleccionadas: <strong>{ventasSeleccionadas.length}</strong>
                </p>
                <p style={{ margin: '5px 0' }}>
                  Suma de retenciones: <strong>{formatearMoneda(calcularSumaRetenciones())}</strong>
                </p>
                <p style={{ margin: '5px 0' }}>
                  Monto disponible: <strong>{formatearMoneda(retencionSeleccionada.monto_retenido_1)}</strong>
                </p>
                {calcularSumaRetenciones() > parseFloat(retencionSeleccionada.monto_retenido_1 || 0) && (
                  <div style={{ marginTop: '10px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', color: '#e74c3c' }}>
                      Justificación (requerida):
                    </label>
                    <textarea
                      value={justificacion}
                      onChange={(e) => setJustificacion(e.target.value)}
                      placeholder="Explica por qué la suma excede el monto disponible..."
                      style={{
                        width: '100%',
                        padding: '8px',
                        border: '1px solid #e74c3c',
                        borderRadius: '3px',
                        minHeight: '60px',
                        fontFamily: 'inherit'
                      }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* BOTONES */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
              <button
                onClick={cerrarModal}
                style={{
                  padding: '10px 20px',
                  background: '#95a5a6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer'
                }}
              >
                Cancelar
              </button>
              <button
                onClick={aplicarRetencion}
                disabled={ventasSeleccionadas.length === 0}
                style={{
                  padding: '10px 20px',
                  background: ventasSeleccionadas.length === 0 ? '#bdc3c7' : '#27ae60',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: ventasSeleccionadas.length === 0 ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold'
                }}
              >
                ✅ Aplicar Retención
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GestionRetenciones;






