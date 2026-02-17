import React, { useState, useEffect } from 'react';
import { usePeriodo } from '../contexts/PeriodoContext';

const LibroLiquidaciones = ({ clienteInfo, volverAlInicio }) => {
  const { periodoFormateado } = usePeriodo();
  const [liquidaciones, setLiquidaciones] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    cargarLiquidaciones();
  }, [clienteInfo, periodoFormateado]);

  const cargarLiquidaciones = async () => {
    if (!clienteInfo?.id) return;
    
    setCargando(true);
    setError('');
    
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/liquidaciones/listar/?empresa_id=${clienteInfo.id}&periodo=${periodoFormateado}`
      );
      
      if (!response.ok) {
        throw new Error('Error al cargar liquidaciones');
      }
      
      const data = await response.json();
      setLiquidaciones(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  const descargarCSV161 = async () => {
    if (!clienteInfo?.id) {
      alert('No hay empresa seleccionada');
      return;
    }

    try {
      const url = `http://127.0.0.1:8000/api/reportes/csv-161/?empresa_id=${clienteInfo.id}&periodo=${periodoFormateado}`;
      window.open(url, '_blank');
    } catch (err) {
      alert('Error al descargar CSV 161: ' + err.message);
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

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div>
          <h2 style={{ margin: 0, color: '#2c3e50' }}>📋 Libro de Liquidaciones</h2>
          <p style={{ color: '#7f8c8d', margin: '5px 0 0 0' }}>
            Período: <strong>{periodoFormateado}</strong> | Empresa: <strong>{clienteInfo?.nombre}</strong>
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={descargarCSV161}
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
            📥 Descargar CSV 161
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

      {/* TABLA */}
      {error && (
        <div style={{ padding: '15px', background: '#e74c3c', color: 'white', borderRadius: '5px', marginBottom: '20px' }}>
          ❌ {error}
        </div>
      )}

      {cargando ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>Cargando liquidaciones...</p>
        </div>
      ) : liquidaciones.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', background: 'white', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
          <p style={{ color: '#7f8c8d', fontSize: '1.1em' }}>No hay liquidaciones registradas para este período.</p>
        </div>
      ) : (
        <div style={{ background: 'white', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#34495e', color: 'white' }}>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #2c3e50' }}>Fecha</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Agente</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>NIT Agente</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Monto Operación</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>IVA Percibido 2%</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Comisión</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Líquido a Pagar</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Código Generación</th>
              </tr>
            </thead>
            <tbody>
              {liquidaciones.map((liq, index) => (
                <tr
                  key={liq.id || index}
                  style={{
                    borderBottom: '1px solid #ecf0f1',
                    background: index % 2 === 0 ? 'white' : '#f8f9fa'
                  }}
                >
                  <td style={{ padding: '12px' }}>{formatearFecha(liq.fecha_documento)}</td>
                  <td style={{ padding: '12px' }}>{liq.nombre_agente || '-'}</td>
                  <td style={{ padding: '12px' }}>{liq.nit_agente || '-'}</td>
                  <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold' }}>
                    {formatearMoneda(liq.monto_operacion)}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>
                    {formatearMoneda(liq.iva_percibido_2)}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>
                    {formatearMoneda(liq.comision)}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', color: '#27ae60' }}>
                    {formatearMoneda(liq.liquido_pagar)}
                  </td>
                  <td style={{ padding: '12px', fontSize: '0.85em', color: '#7f8c8d' }}>
                    {liq.codigo_generacion ? liq.codigo_generacion.substring(0, 20) + '...' : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ background: '#ecf0f1', fontWeight: 'bold' }}>
                <td colSpan="3" style={{ padding: '12px', textAlign: 'right' }}>TOTALES:</td>
                <td style={{ padding: '12px', textAlign: 'right' }}>
                  {formatearMoneda(liquidaciones.reduce((sum, liq) => sum + parseFloat(liq.monto_operacion || 0), 0))}
                </td>
                <td style={{ padding: '12px', textAlign: 'right' }}>
                  {formatearMoneda(liquidaciones.reduce((sum, liq) => sum + parseFloat(liq.iva_percibido_2 || 0), 0))}
                </td>
                <td style={{ padding: '12px', textAlign: 'right' }}>
                  {formatearMoneda(liquidaciones.reduce((sum, liq) => sum + parseFloat(liq.comision || 0), 0))}
                </td>
                <td style={{ padding: '12px', textAlign: 'right', color: '#27ae60' }}>
                  {formatearMoneda(liquidaciones.reduce((sum, liq) => sum + parseFloat(liq.liquido_pagar || 0), 0))}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
};

export default LibroLiquidaciones;

