import React, { useState, useEffect } from 'react';

// --- IMPORTAMOS LOS MÓDULOS ---
import SeleccionEmpresa from './components/SeleccionEmpresa';
import PortalModulos from './components/PortalModulos';
import { PeriodoProvider, usePeriodo } from './contexts/PeriodoContext';

// Módulo Contabilidad
import FormularioCompras from './components/FormularioCompras';
import LibrosIVA from './components/LibrosIVA';
import LibroLiquidaciones from './components/LibroLiquidaciones';
import GestionRetenciones from './components/GestionRetenciones';
import CargaMasiva from './components/CargaMasiva';

// Módulo Facturación (a crear)
import PanelFacturacion from './components/PanelFacturacion';
import NuevaFactura from './components/NuevaFactura';

// Componente interno que usa el contexto
function AppContent() {
  const { mes, anio, empresaSeleccionada, setMes, setAnio, setEmpresaSeleccionada } = usePeriodo();
  const [empresaActual, setEmpresaActual] = useState(null);
  const [moduloActual, setModuloActual] = useState(null); // 'facturacion' o 'contabilidad'
  const [vistaActual, setVistaActual] = useState("dashboard");
  const [idEdicion, setIdEdicion] = useState(null);
  const [tipoEdicion, setTipoEdicion] = useState(null);

  // Sincronizar empresaActual con el contexto cuando cambia
  useEffect(() => {
    if (empresaActual) {
      setEmpresaSeleccionada(empresaActual);
    }
  }, [empresaActual, setEmpresaSeleccionada]);

  // --- SI NO HAY EMPRESA SELECCIONADA, MOSTRAMOS EL SELECTOR ---
  if (!empresaActual) {
    return <SeleccionEmpresa alSeleccionar={(empresa) => setEmpresaActual(empresa)} />;
  }

  // --- SI HAY EMPRESA PERO NO MÓDULO, MOSTRAMOS EL PORTAL ---
  if (!moduloActual) {
    return (
      <PortalModulos
        empresa={empresaActual}
        onSeleccionarModulo={(modulo) => {
          setModuloActual(modulo);
          setVistaActual("dashboard");
        }}
        onCambiarEmpresa={() => {
          setEmpresaActual(null);
          setModuloActual(null);
          setEmpresaSeleccionada(null);
        }}
      />
    );
  }

  // --- LOGOUT / CAMBIAR EMPRESA ---
  const cerrarSesion = () => {
    setEmpresaActual(null);
    setModuloActual(null);
    setEmpresaSeleccionada(null);
    setVistaActual("dashboard");
  };

  const volverAlPortal = () => {
    setModuloActual(null);
    setVistaActual("dashboard");
  };

  // Generar lista de años (2022 hasta año actual + 1)
  const anios = [];
  const anioActual = new Date().getFullYear();
  for (let a = 2022; a <= anioActual + 1; a++) {
    anios.push(a);
  }

  // Nombres de meses
  const meses = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  // --- RENDERIZADO PRINCIPAL ---
  return (
    <div style={{ fontFamily: 'Arial, sans-serif', background: '#ecf0f1', minHeight: '100vh' }}>
      
      {/* BARRA SUPERIOR (NAVBAR) */}
      <div style={{ background: 'white', padding: '15px 30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.5em' }}>{moduloActual === 'facturacion' ? '🧾' : '📊'}</span>
            <h1 style={{ margin: 0, fontSize: '1.2em', color: '#2c3e50' }}>
              {moduloActual === 'facturacion' ? 'Facturación e Ingresos' : 'Contabilidad e Impuestos'}
            </h1>
        </div>
        
        {/* SELECTORES DE PERÍODO Y EMPRESA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#f8f9fa', padding: '8px 15px', borderRadius: '5px' }}>
                <label style={{ fontSize: '0.9em', color: '#7f8c8d', fontWeight: 'bold' }}>Período:</label>
                <select 
                    value={mes} 
                    onChange={(e) => setMes(parseInt(e.target.value))}
                    style={{ padding: '5px 10px', border: '1px solid #ddd', borderRadius: '3px', fontSize: '0.9em' }}
                >
                    {meses.map((nombre, index) => (
                        <option key={index + 1} value={index + 1}>{nombre}</option>
                    ))}
                </select>
                <select 
                    value={anio} 
                    onChange={(e) => setAnio(parseInt(e.target.value))}
                    style={{ padding: '5px 10px', border: '1px solid #ddd', borderRadius: '3px', fontSize: '0.9em' }}
                >
                    {anios.map(a => (
                        <option key={a} value={a}>{a}</option>
                    ))}
                </select>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 15px', background: '#e8f5e9', borderRadius: '5px' }}>
                <span style={{ fontSize: '0.9em', color: '#7f8c8d', fontWeight: 'bold' }}>Empresa:</span>
                <span style={{ color: '#27ae60', fontWeight: 'bold', fontSize: '1em' }}>{empresaActual.nombre}</span>
            </div>
            
            <button onClick={volverAlPortal} style={{ padding: '8px 15px', background: '#95a5a6', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
                🔄 Módulos
            </button>
            
            <button onClick={cerrarSesion} style={{ padding: '8px 15px', background: '#c0392b', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
                🔒 Salir
            </button>
        </div>
      </div>

      {/* CONTENIDO CAMBIANTE SEGÚN EL MÓDULO */}
      <div style={{ padding: '30px' }}>
        
        {/* ============================================
            MÓDULO DE FACTURACIÓN
        ============================================ */}
        {moduloActual === 'facturacion' && (
          <>
            {vistaActual === "dashboard" && (
              <PanelFacturacion
                empresa={empresaActual}
                onNuevaFactura={() => setVistaActual("nuevaFactura")}
                onVerFactura={(id) => {
                  setIdEdicion(id);
                  setVistaActual("verFactura");
                }}
              />
            )}

            {vistaActual === "nuevaFactura" && (
              <NuevaFactura
                empresa={empresaActual}
                ventaId={idEdicion}
                volverAlInicio={() => {
                  setVistaActual("dashboard");
                  setIdEdicion(null);
                }}
              />
            )}
          </>
        )}

        {/* ============================================
            MÓDULO DE CONTABILIDAD
        ============================================ */}
        {moduloActual === 'contabilidad' && (
          <>
            {/* DASHBOARD CONTABILIDAD */}
            {vistaActual === "dashboard" && (
              <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
                <h2>Hola, Contador 👋</h2>
                <p>¿Qué deseas registrar hoy para <strong>{empresaActual.nombre}</strong>?</p>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginTop: '30px' }}>
                  <div onClick={() => setVistaActual("nuevaCompra")} 
                       style={{ background: '#3498db', color: 'white', padding: '30px', borderRadius: '10px', cursor: 'pointer', textAlign: 'center', transition: '0.3s' }}>
                    <span style={{ fontSize: '3em', display: 'block' }}>🛍️</span>
                    <h3>Nueva Compra</h3>
                  </div>

                  <div onClick={() => setVistaActual("librosIVA")} 
                       style={{ background: '#16a085', color: 'white', padding: '30px', borderRadius: '10px', cursor: 'pointer', textAlign: 'center', transition: '0.3s' }}>
                    <span style={{ fontSize: '3em', display: 'block' }}>📊</span>
                    <h3>Libros de IVA</h3>
                  </div>

                  <div onClick={() => setVistaActual("liquidaciones")} 
                       style={{ background: '#e67e22', color: 'white', padding: '30px', borderRadius: '10px', cursor: 'pointer', textAlign: 'center', transition: '0.3s' }}>
                    <span style={{ fontSize: '3em', display: 'block' }}>💳</span>
                    <h3>Liquidaciones</h3>
                  </div>

                  <div onClick={() => setVistaActual("retenciones")} 
                       style={{ background: '#8e44ad', color: 'white', padding: '30px', borderRadius: '10px', cursor: 'pointer', textAlign: 'center', transition: '0.3s' }}>
                    <span style={{ fontSize: '3em', display: 'block' }}>🔒</span>
                    <h3>Retenciones</h3>
                  </div>

                  <div onClick={() => setVistaActual("cargaMasiva")} 
                       style={{ background: '#e74c3c', color: 'white', padding: '30px', borderRadius: '10px', cursor: 'pointer', textAlign: 'center', transition: '0.3s' }}>
                    <span style={{ fontSize: '3em', display: 'block' }}>📤</span>
                    <h3>Carga Masiva DTE</h3>
                  </div>
                </div>
              </div>
            )}

            {/* VISTAS CONTABILIDAD */}
            {vistaActual === "nuevaCompra" && (
              <FormularioCompras 
                clienteInfo={empresaActual} 
                volverAlInicio={() => {
                  setVistaActual("dashboard");
                  setIdEdicion(null);
                  setTipoEdicion(null);
                }}
                compraId={tipoEdicion === 'compra' ? idEdicion : null}
              />
            )}

            {vistaActual === "librosIVA" && (
              <LibrosIVA 
                clienteInfo={empresaActual} 
                volverAlInicio={() => setVistaActual("dashboard")}
                onEditar={(id, tipo) => {
                  setIdEdicion(id);
                  setTipoEdicion(tipo);
                  setVistaActual(tipo === 'compra' ? "nuevaCompra" : "dashboard");
                }}
              />
            )}

            {vistaActual === "liquidaciones" && (
              <LibroLiquidaciones 
                clienteInfo={empresaActual} 
                volverAlInicio={() => setVistaActual("dashboard")}
              />
            )}

            {vistaActual === "retenciones" && (
              <GestionRetenciones 
                clienteInfo={empresaActual} 
                volverAlInicio={() => setVistaActual("dashboard")}
              />
            )}

            {vistaActual === "cargaMasiva" && (
              <CargaMasiva 
                clienteInfo={empresaActual} 
                volverAlInicio={() => setVistaActual("dashboard")}
              />
            )}
          </>
        )}

      </div>
    </div>
  );
}

// Componente principal que envuelve con el Provider
function App() {
  return (
    <PeriodoProvider>
      <AppContent />
    </PeriodoProvider>
  );
}

export default App;
