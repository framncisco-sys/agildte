import React, { useState, useEffect } from 'react';
import { usePeriodo } from '../contexts/PeriodoContext';

const PanelFacturacion = ({ empresa, onNuevaFactura, onVerFactura }) => {
  const { periodoFormateado } = usePeriodo();
  const [ventas, setVentas] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    cargarVentas();
  }, [empresa, periodoFormateado]);

  const cargarVentas = async () => {
    if (!empresa?.id) return;
    
    setCargando(true);
    setError('');
    
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/ventas/listar/?empresa_id=${empresa.id}&periodo=${periodoFormateado}`
      );
      
      if (!response.ok) {
        throw new Error('Error al cargar ventas');
      }
      
      const data = await response.json();
      setVentas(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  const obtenerColorEstado = (estado) => {
    const colores = {
      'Borrador': '#95a5a6',
      'Generado': '#3498db',
      'Enviado': '#f39c12',
      'AceptadoMH': '#27ae60',
      'RechazadoMH': '#e74c3c',
      'Anulado': '#7f8c8d'
    };
    return colores[estado] || '#95a5a6';
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

  const verJsonDTE = async (ventaId) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/ventas/${ventaId}/generar-dte/`);
      if (!response.ok) throw new Error('Error al generar DTE');
      const data = await response.json();
      
      // Mostrar JSON en nueva ventana
      const nuevaVentana = window.open('', '_blank');
      nuevaVentana.document.write(`
        <html>
          <head><title>JSON DTE - Venta ${ventaId}</title></head>
          <body style="font-family: monospace; padding: 20px; background: #f5f5f5;">
            <h2>JSON DTE</h2>
            <pre style="background: white; padding: 15px; border-radius: 5px; overflow: auto;">${JSON.stringify(data.dte_json, null, 2)}</pre>
          </body>
        </html>
      `);
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const verPDFFactura = async (ventaId) => {
    try {
      // CRÍTICO: responseType debe ser 'blob' para manejar PDFs binarios
      const response = await fetch(`http://127.0.0.1:8000/api/ventas/${ventaId}/generar-pdf/`, {
        method: 'GET',
        headers: {
          'Accept': 'application/pdf',
        },
      });
      
      if (!response.ok) {
        throw new Error('Error al generar PDF');
      }
      
      // Obtener el blob de la respuesta
      const blob = await response.blob();
      
      // Crear URL del objeto blob
      const url = window.URL.createObjectURL(blob);
      
      // Abrir el PDF en una nueva ventana
      window.open(url, '_blank');
      
      // Limpiar la URL después de un tiempo (opcional)
      setTimeout(() => window.URL.revokeObjectURL(url), 100);
    } catch (err) {
      alert(`Error al generar PDF: ${err.message}`);
    }
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div>
          <h2 style={{ margin: 0, color: '#2c3e50' }}>🧾 Panel de Facturación</h2>
          <p style={{ color: '#7f8c8d', margin: '5px 0 0 0' }}>
            Período: <strong>{periodoFormateado}</strong> | Empresa: <strong>{empresa?.nombre}</strong>
          </p>
        </div>
        <button
          onClick={onNuevaFactura}
          style={{
            padding: '12px 30px',
            background: '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 'bold',
            fontSize: '1em',
            boxShadow: '0 4px 6px rgba(52, 152, 219, 0.3)'
          }}
        >
          ➕ Nueva Factura
        </button>
      </div>

      {/* ERROR */}
      {error && (
        <div style={{ padding: '15px', background: '#e74c3c', color: 'white', borderRadius: '5px', marginBottom: '20px' }}>
          ❌ {error}
        </div>
      )}

      {/* TABLA DE DOCUMENTOS */}
      {cargando ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>Cargando documentos...</p>
        </div>
      ) : ventas.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', background: 'white', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '4em', marginBottom: '20px' }}>📄</div>
          <p style={{ color: '#7f8c8d', fontSize: '1.1em' }}>No hay documentos emitidos para este período.</p>
          <button
            onClick={onNuevaFactura}
            style={{
              marginTop: '20px',
              padding: '12px 30px',
              background: '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            Crear Primera Factura
          </button>
        </div>
      ) : (
        <div style={{ background: 'white', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#34495e', color: 'white' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>Fecha</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Cliente</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Número Control</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Total</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Estado DTE</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {ventas.map((venta, index) => (
                <tr
                  key={venta.id || index}
                  style={{
                    borderBottom: '1px solid #ecf0f1',
                    background: index % 2 === 0 ? 'white' : '#f8f9fa'
                  }}
                >
                  <td style={{ padding: '12px' }}>{formatearFecha(venta.fecha_emision)}</td>
                  <td style={{ padding: '12px' }}>
                    {venta.nombre_receptor || venta.cliente?.nombre || 'Consumidor Final'}
                  </td>
                  <td style={{ padding: '12px', fontSize: '0.85em', fontFamily: 'monospace', color: '#7f8c8d' }}>
                    {venta.numero_control || '-'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold' }}>
                    {formatearMoneda(parseFloat(venta.venta_gravada || 0) + parseFloat(venta.debito_fiscal || 0))}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <span
                      style={{
                        padding: '5px 12px',
                        borderRadius: '15px',
                        background: obtenerColorEstado(venta.estado_dte || 'Borrador'),
                        color: 'white',
                        fontSize: '0.85em',
                        fontWeight: 'bold'
                      }}
                    >
                      {venta.estado_dte || 'Borrador'}
                    </span>
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap' }}>
                      <button
                        onClick={() => verPDFFactura(venta.id)}
                        style={{
                          padding: '5px 10px',
                          background: '#e74c3c',
                          color: 'white',
                          border: 'none',
                          borderRadius: '5px',
                          cursor: 'pointer',
                          fontSize: '0.8em'
                        }}
                        title="Ver PDF"
                      >
                        📄 PDF
                      </button>
                      <button
                        onClick={() => verJsonDTE(venta.id)}
                        style={{
                          padding: '5px 10px',
                          background: '#3498db',
                          color: 'white',
                          border: 'none',
                          borderRadius: '5px',
                          cursor: 'pointer',
                          fontSize: '0.8em'
                        }}
                        title="Ver JSON DTE"
                      >
                        📋 JSON
                      </button>
                      <button
                        onClick={() => onVerFactura(venta.id)}
                        style={{
                          padding: '5px 10px',
                          background: '#27ae60',
                          color: 'white',
                          border: 'none',
                          borderRadius: '5px',
                          cursor: 'pointer',
                          fontSize: '0.8em'
                        }}
                        title="Ver Detalles"
                      >
                        👁️ Ver
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default PanelFacturacion;

