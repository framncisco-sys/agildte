import React, { useState, useEffect } from 'react';

// --- IMPORTAMOS LOS MÓDULOS QUE CREASTE ---
import SeleccionEmpresa from './components/SeleccionEmpresa';
import FormularioCompras from './components/FormularioCompras';
import FormularioVentas from './components/FormularioVentas';
import LibrosIVA from './components/LibrosIVA';
import { PeriodoProvider, usePeriodo } from './contexts/PeriodoContext';

// Componente interno que usa el contexto
function AppContent() {
  const { mes, anio, empresaSeleccionada, setMes, setAnio, setEmpresaSeleccionada } = usePeriodo();
  const [empresaActual, setEmpresaActual] = useState(null);
  const [vistaActual, setVistaActual] = useState("dashboard");
  const [idEdicion, setIdEdicion] = useState(null); // ID para edición
  const [tipoEdicion, setTipoEdicion] = useState(null); // 'compra' o 'venta'

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

  // --- LOGOUT / CAMBIAR EMPRESA ---
  const cerrarSesion = () => {
    setEmpresaActual(null);
    setEmpresaSeleccionada(null);
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

  // --- RENDERIZADO PRINCIPAL (DASHBOARD Y FORMULARIOS) ---
  return (
    <div style={{ fontFamily: 'Arial, sans-serif', background: '#ecf0f1', minHeight: '100vh' }}>
      
      {/* BARRA SUPERIOR (NAVBAR) - CON SELECTORES DE PERÍODO */}
      <div style={{ background: 'white', padding: '15px 30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.5em' }}>📊</span>
            <h1 style={{ margin: 0, fontSize: '1.2em', color: '#2c3e50' }}>Sistema Contable SA</h1>
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
            
            <button onClick={cerrarSesion} style={{ padding: '8px 15px', background: '#c0392b', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
                🔒 Salir
            </button>
        </div>
      </div>

      {/* CONTENIDO CAMBIANTE SEGÚN LA VISTA */}
      <div style={{ padding: '30px' }}>
        
        {/* 1. VISTA DASHBOARD (MENU PRINCIPAL) */}
        {vistaActual === "dashboard" && (
            <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
                <h2>Hola, Contador 👋</h2>
                <p>¿Qué deseas registrar hoy para <strong>{empresaActual.nombre}</strong>?</p>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginTop: '30px' }}>
                    {/* BOTÓN COMPRA */}
                    <div onClick={() => setVistaActual("nuevaCompra")} 
                         style={{ background: '#3498db', color: 'white', padding: '30px', borderRadius: '10px', cursor: 'pointer', textAlign: 'center', transition: '0.3s' }}>
                        <span style={{ fontSize: '3em', display: 'block' }}>🛍️</span>
                        <h3>Nueva Compra</h3>
                    </div>

                    {/* BOTÓN VENTA */}
                    <div onClick={() => setVistaActual("nuevaVenta")} 
                         style={{ background: '#9b59b6', color: 'white', padding: '30px', borderRadius: '10px', cursor: 'pointer', textAlign: 'center', transition: '0.3s' }}>
                        <span style={{ fontSize: '3em', display: 'block' }}>💰</span>
                        <h3>Nueva Venta</h3>
                    </div>

                    {/* BOTÓN LIBROS DE IVA */}
                    <div onClick={() => setVistaActual("librosIVA")} 
                         style={{ background: '#16a085', color: 'white', padding: '30px', borderRadius: '10px', cursor: 'pointer', textAlign: 'center', transition: '0.3s' }}>
                        <span style={{ fontSize: '3em', display: 'block' }}>📊</span>
                        <h3>Libros de IVA</h3>
                    </div>
                </div>
            </div>
        )}

        {/* 2. VISTA FORMULARIO COMPRAS */}
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

        {/* 3. VISTA FORMULARIO VENTAS */}
        {vistaActual === "nuevaVenta" && (
            <FormularioVentas 
                clienteInfo={empresaActual} 
                volverAlInicio={() => {
                  setVistaActual("dashboard");
                  setIdEdicion(null);
                  setTipoEdicion(null);
                }}
                ventaId={tipoEdicion === 'venta' ? idEdicion : null}
            />
        )}

        {/* 4. VISTA LIBROS DE IVA */}
        {vistaActual === "librosIVA" && (
            <LibrosIVA 
                clienteInfo={empresaActual} 
                volverAlInicio={() => setVistaActual("dashboard")}
                onEditar={(id, tipo) => {
                  setIdEdicion(id);
                  setTipoEdicion(tipo);
                  setVistaActual(tipo === 'compra' ? "nuevaCompra" : "nuevaVenta");
                }}
            />
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