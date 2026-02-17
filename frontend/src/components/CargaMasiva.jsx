import React, { useState, useRef } from 'react';
import { usePeriodo } from '../contexts/PeriodoContext';

const CargaMasiva = ({ clienteInfo, volverAlInicio }) => {
  const { periodoFormateado } = usePeriodo();
  const [archivosSeleccionados, setArchivosSeleccionados] = useState([]);
  const [resultados, setResultados] = useState([]);
  const [procesando, setProcesando] = useState(false);
  const [resumen, setResumen] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    // Filtrar solo archivos JSON
    const jsonFiles = files.filter(file => file.name.toLowerCase().endsWith('.json'));
    
    if (jsonFiles.length !== files.length) {
      alert('⚠️ Solo se aceptan archivos JSON. Se ignoraron otros tipos de archivo.');
    }
    
    setArchivosSeleccionados(jsonFiles);
    setResultados([]);
    setResumen(null);
  };

  const procesarArchivos = async () => {
    if (archivosSeleccionados.length === 0) {
      alert('⚠️ Por favor selecciona al menos un archivo JSON');
      return;
    }

    if (!clienteInfo?.id) {
      alert('⚠️ No hay empresa seleccionada');
      return;
    }

    setProcesando(true);
    setResultados([]);
    setResumen(null);

    // Inicializar resultados con estado "Cargando"
    const resultadosIniciales = archivosSeleccionados.map(archivo => ({
      nombreArchivo: archivo.name,
      estado: 'Cargando',
      tipoDetectado: '-',
      mensaje: 'Procesando...',
      color: '#3498db'
    }));
    setResultados(resultadosIniciales);

    try {
      // Preparar FormData para enviar archivos
      const formData = new FormData();
      formData.append('empresa_id', clienteInfo.id);
      
      archivosSeleccionados.forEach(archivo => {
        formData.append('archivos', archivo);
      });

      // Enviar al endpoint
      const response = await fetch('http://127.0.0.1:8000/api/sistema/procesar-json-dte/', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Error desconocido' }));
        throw new Error(errorData.error || `Error ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Procesar resultados
      const nuevosResultados = [];
      
      // Procesar liquidaciones
      if (data.liquidaciones && data.liquidaciones.length > 0) {
        data.liquidaciones.forEach(item => {
          nuevosResultados.push({
            nombreArchivo: item.archivo,
            estado: item.estado === 'Guardado' ? 'Éxito' : item.estado,
            tipoDetectado: 'Liquidación (DTE-09)',
            mensaje: item.estado === 'Guardado' 
              ? `Guardado: ${item.agente || 'N/A'} - $${(item.monto || 0).toFixed(2)}`
              : item.estado === 'Duplicado' ? 'Documento duplicado' : item.estado,
            color: item.estado === 'Guardado' ? '#27ae60' : '#f39c12'
          });
        });
      }

      // Procesar retenciones
      if (data.retenciones && data.retenciones.length > 0) {
        data.retenciones.forEach(item => {
          nuevosResultados.push({
            nombreArchivo: item.archivo,
            estado: item.estado === 'Guardado' ? 'Éxito' : item.estado,
            tipoDetectado: 'Retención (DTE-07)',
            mensaje: item.estado === 'Guardado'
              ? `Guardado: ${item.agente || 'N/A'} - Retención: $${(item.monto_retenido || 0).toFixed(2)}`
              : item.estado === 'Duplicado' ? 'Documento duplicado' : item.estado,
            color: item.estado === 'Guardado' ? '#27ae60' : '#f39c12'
          });
        });
      }

      // Procesar compras
      if (data.compras && data.compras.length > 0) {
        data.compras.forEach(item => {
          nuevosResultados.push({
            nombreArchivo: item.archivo,
            estado: item.estado === 'Guardado' ? 'Éxito' : item.estado,
            tipoDetectado: `Compra (DTE-${item.tipo_dte || '03'})`,
            mensaje: item.estado === 'Guardado'
              ? `Guardado: ${item.proveedor || 'N/A'} - Total: $${(item.total || 0).toFixed(2)}`
              : item.estado === 'Duplicado' ? 'Documento duplicado' : item.estado,
            color: item.estado === 'Guardado' ? '#27ae60' : '#f39c12'
          });
        });
      }

      // Procesar errores
      if (data.errores && data.errores.length > 0) {
        data.errores.forEach(item => {
          nuevosResultados.push({
            nombreArchivo: item.archivo,
            estado: 'Error',
            tipoDetectado: 'No detectado',
            mensaje: item.motivo || 'Error desconocido',
            color: '#e74c3c'
          });
        });
      }

      // Actualizar resultados
      setResultados(nuevosResultados);
      
      // Guardar resumen
      if (data.resumen) {
        setResumen(data.resumen);
      }

      // Mostrar mensaje de éxito
      if (data.resumen) {
        const totalExitosos = (data.resumen.liquidaciones_guardadas || 0) + 
                              (data.resumen.retenciones_guardadas || 0) + 
                              (data.resumen.compras_guardadas || 0);
        
        if (totalExitosos > 0) {
          alert(`✅ Procesamiento completado:\n- ${totalExitosos} documento(s) guardado(s)\n- ${data.resumen.duplicados || 0} duplicado(s)\n- ${data.resumen.errores || 0} error(es)`);
        }
      }

    } catch (error) {
      // Marcar todos como error
      const resultadosError = archivosSeleccionados.map(archivo => ({
        nombreArchivo: archivo.name,
        estado: 'Error',
        tipoDetectado: '-',
        mensaje: error.message || 'Error al procesar',
        color: '#e74c3c'
      }));
      setResultados(resultadosError);
      alert(`❌ Error al procesar archivos: ${error.message}`);
    } finally {
      setProcesando(false);
    }
  };

  const limpiarSeleccion = () => {
    setArchivosSeleccionados([]);
    setResultados([]);
    setResumen(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const obtenerIconoEstado = (estado) => {
    switch (estado) {
      case 'Éxito':
        return '✅';
      case 'Error':
        return '❌';
      case 'Duplicado':
        return '⚠️';
      case 'Cargando':
        return '⏳';
      default:
        return '📄';
    }
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div>
          <h2 style={{ margin: 0, color: '#2c3e50' }}>📤 Carga Masiva de DTEs</h2>
          <p style={{ color: '#7f8c8d', margin: '5px 0 0 0' }}>
            Empresa: <strong>{clienteInfo?.nombre}</strong> | Período: <strong>{periodoFormateado}</strong>
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
            cursor: 'pointer'
          }}
        >
          ← Volver
        </button>
      </div>

      {/* ÁREA DE CARGA */}
      <div style={{ 
        background: 'white', 
        borderRadius: '10px', 
        padding: '30px', 
        boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
        marginBottom: '30px'
      }}>
        <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Seleccionar Archivos JSON</h3>
        <p style={{ color: '#7f8c8d', marginBottom: '20px' }}>
          Selecciona uno o más archivos JSON de DTEs. El sistema clasificará automáticamente cada documento.
        </p>

        <div style={{ display: 'flex', gap: '15px', alignItems: 'center', flexWrap: 'wrap' }}>
          <label
            style={{
              padding: '12px 24px',
              background: '#3498db',
              color: 'white',
              borderRadius: '5px',
              cursor: 'pointer',
              display: 'inline-block',
              fontWeight: 'bold'
            }}
          >
            📁 Seleccionar Archivos
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".json"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
          </label>

          {archivosSeleccionados.length > 0 && (
            <>
              <span style={{ color: '#7f8c8d', fontWeight: 'bold' }}>
                {archivosSeleccionados.length} archivo(s) seleccionado(s)
              </span>
              <button
                onClick={limpiarSeleccion}
                style={{
                  padding: '8px 15px',
                  background: '#e74c3c',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer'
                }}
              >
                🗑️ Limpiar
              </button>
            </>
          )}
        </div>

        {archivosSeleccionados.length > 0 && (
          <div style={{ marginTop: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '5px' }}>
            <strong style={{ display: 'block', marginBottom: '10px', color: '#2c3e50' }}>
              Archivos seleccionados:
            </strong>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#7f8c8d' }}>
              {archivosSeleccionados.map((archivo, index) => (
                <li key={index} style={{ marginBottom: '5px' }}>
                  {archivo.name} ({(archivo.size / 1024).toFixed(2)} KB)
                </li>
              ))}
            </ul>
          </div>
        )}

        <div style={{ marginTop: '20px' }}>
          <button
            onClick={procesarArchivos}
            disabled={procesando || archivosSeleccionados.length === 0}
            style={{
              padding: '12px 30px',
              background: procesando || archivosSeleccionados.length === 0 ? '#bdc3c7' : '#27ae60',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: procesando || archivosSeleccionados.length === 0 ? 'not-allowed' : 'pointer',
              fontWeight: 'bold',
              fontSize: '1em'
            }}
          >
            {procesando ? '⏳ Procesando...' : '🚀 Procesar Archivos'}
          </button>
        </div>
      </div>

      {/* RESUMEN */}
      {resumen && (
        <div style={{
          background: 'white',
          borderRadius: '10px',
          padding: '20px',
          boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
          marginBottom: '30px'
        }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>📊 Resumen del Procesamiento</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '15px' }}>
            <div style={{ padding: '15px', background: '#e8f5e9', borderRadius: '5px' }}>
              <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#27ae60' }}>
                {resumen.liquidaciones_guardadas || 0}
              </div>
              <div style={{ color: '#7f8c8d', fontSize: '0.9em' }}>Liquidaciones</div>
            </div>
            <div style={{ padding: '15px', background: '#e8f5e9', borderRadius: '5px' }}>
              <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#27ae60' }}>
                {resumen.retenciones_guardadas || 0}
              </div>
              <div style={{ color: '#7f8c8d', fontSize: '0.9em' }}>Retenciones</div>
            </div>
            <div style={{ padding: '15px', background: '#e8f5e9', borderRadius: '5px' }}>
              <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#27ae60' }}>
                {resumen.compras_guardadas || 0}
              </div>
              <div style={{ color: '#7f8c8d', fontSize: '0.9em' }}>Compras</div>
            </div>
            <div style={{ padding: '15px', background: '#fff3cd', borderRadius: '5px' }}>
              <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#f39c12' }}>
                {resumen.duplicados || 0}
              </div>
              <div style={{ color: '#7f8c8d', fontSize: '0.9em' }}>Duplicados</div>
            </div>
            <div style={{ padding: '15px', background: '#f8d7da', borderRadius: '5px' }}>
              <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#e74c3c' }}>
                {resumen.errores || 0}
              </div>
              <div style={{ color: '#7f8c8d', fontSize: '0.9em' }}>Errores</div>
            </div>
          </div>
        </div>
      )}

      {/* TABLA DE RESULTADOS */}
      {resultados.length > 0 && (
        <div style={{
          background: 'white',
          borderRadius: '10px',
          boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
          overflow: 'hidden'
        }}>
          <h3 style={{ padding: '20px 20px 0 20px', margin: 0, color: '#2c3e50' }}>
            📋 Resultados del Procesamiento
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#34495e', color: 'white' }}>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #2c3e50' }}>
                    Nombre Archivo
                  </th>
                  <th style={{ padding: '12px', textAlign: 'center' }}>Estado</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Tipo Detectado</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Mensaje</th>
                </tr>
              </thead>
              <tbody>
                {resultados.map((resultado, index) => (
                  <tr
                    key={index}
                    style={{
                      borderBottom: '1px solid #ecf0f1',
                      background: index % 2 === 0 ? 'white' : '#f8f9fa'
                    }}
                  >
                    <td style={{ padding: '12px', fontWeight: 'bold', color: '#2c3e50' }}>
                      {resultado.nombreArchivo}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <span
                        style={{
                          padding: '5px 12px',
                          borderRadius: '5px',
                          background: resultado.color,
                          color: 'white',
                          fontSize: '0.85em',
                          fontWeight: 'bold',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                      >
                        {obtenerIconoEstado(resultado.estado)} {resultado.estado}
                      </span>
                    </td>
                    <td style={{ padding: '12px', color: '#7f8c8d' }}>
                      {resultado.tipoDetectado}
                    </td>
                    <td style={{ padding: '12px', color: '#2c3e50' }}>
                      {resultado.mensaje}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* MENSAJE INICIAL */}
      {resultados.length === 0 && !procesando && (
        <div style={{
          textAlign: 'center',
          padding: '60px 20px',
          background: 'white',
          borderRadius: '10px',
          boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
        }}>
          <div style={{ fontSize: '4em', marginBottom: '20px' }}>📤</div>
          <p style={{ color: '#7f8c8d', fontSize: '1.1em' }}>
            Selecciona archivos JSON de DTEs para comenzar el procesamiento
          </p>
        </div>
      )}
    </div>
  );
};

export default CargaMasiva;






