import React, { useState, useEffect } from 'react';

const SeleccionEmpresa = ({ alSeleccionar }) => {
  const [empresas, setEmpresas] = useState([]);
  const [modoCrear, setModoCrear] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  
  // Estados para nueva empresa
  const [nuevoNombre, setNuevoNombre] = useState("");
  const [nuevoNrc, setNuevoNrc] = useState("");
  const [nuevoNit, setNuevoNit] = useState("");
  const [nuevoEsImportador, setNuevoEsImportador] = useState(false);

  // Cargar empresas al iniciar este componente
  useEffect(() => {
    cargarEmpresas();
  }, []);

  const cargarEmpresas = async () => {
    setCargando(true);
    setError(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/empresas/');
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: `Error ${res.status}: ${res.statusText}` }));
        throw new Error(errorData.detail || `Error ${res.status}: ${res.statusText}`);
      }
      
      const data = await res.json();
      // DRF puede devolver un array directamente o un objeto con 'results'
      const empresasList = Array.isArray(data) ? data : (data.results || []);
      setEmpresas(empresasList);
    } catch (err) {
      console.error("Error cargando empresas:", err);
      setError(err.message || "Error al conectar con el servidor. Verifica que el backend esté corriendo en http://127.0.0.1:8000");
      setEmpresas([]);
    } finally {
      setCargando(false);
    }
  };

  const guardarNuevaEmpresa = async () => {
    if(!nuevoNombre || !nuevoNrc) { 
      alert("Nombre y NRC son obligatorios"); 
      return; 
    }

    const payload = { 
        nombre: nuevoNombre, 
        nrc: nuevoNrc, 
        nit: nuevoNit || null, 
        es_importador: nuevoEsImportador 
    };

    try {
      const res = await fetch('http://127.0.0.1:8000/api/empresas/', { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify(payload) 
      });

      if(res.ok) { 
          const nuevaEmpresa = await res.json();
          alert("✅ Empresa Creada"); 
          cargarEmpresas(); 
          setModoCrear(false); 
          // Limpiar campos
          setNuevoNombre(""); 
          setNuevoNrc(""); 
          setNuevoNit(""); 
          setNuevoEsImportador(false);
      } else {
          const errorData = await res.json().catch(() => ({ detail: `Error ${res.status}` }));
          const mensajeError = errorData.nrc?.[0] || errorData.detail || "Error al crear la empresa";
          alert(`❌ Error: ${mensajeError}`); 
      }
    } catch (err) {
      console.error("Error guardando empresa:", err);
      alert("❌ Error de conexión. Verifica que el backend esté corriendo.");
    }
  };

  return (
    <div style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#2c3e50' }}>
      <div style={{ background: 'white', padding: '40px', borderRadius: '10px', width: '500px', textAlign: 'center', boxShadow: '0 4px 15px rgba(0,0,0,0.2)' }}>
        
        {/* --- PANTALLA LISTA DE EMPRESAS --- */}
        {!modoCrear && (
            <>
                <h2>Selecciona una Empresa</h2>
                <div style={{ textAlign: 'right', marginBottom: '10px' }}>
                    <button onClick={() => setModoCrear(true)} style={{ padding: '8px 15px', background: '#27ae60', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
                        ➕ Nueva Empresa
                    </button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '300px', overflowY: 'auto' }}>
                    {cargando && (
                        <p style={{ padding: '20px', color: '#7f8c8d' }}>⏳ Cargando empresas...</p>
                    )}
                    {!cargando && error && (
                        <div style={{ padding: '15px', background: '#fee', border: '1px solid #fcc', borderRadius: '5px', color: '#c33' }}>
                            <strong>❌ Error:</strong> {error}
                            <br />
                            <button onClick={cargarEmpresas} style={{ marginTop: '10px', padding: '5px 10px', background: '#27ae60', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer' }}>
                                🔄 Reintentar
                            </button>
                        </div>
                    )}
                    {!cargando && !error && empresas.length === 0 && (
                        <p style={{ padding: '20px', color: '#7f8c8d' }}>No hay empresas registradas. Crea una nueva empresa para comenzar.</p>
                    )}
                    {!cargando && !error && empresas.map(empresa => (
                        <div key={empresa.id || empresa.nrc} onClick={() => alSeleccionar(empresa)} 
                             style={{ padding: '15px', border: '1px solid #eee', borderRadius: '5px', cursor: 'pointer', textAlign: 'left', background: '#f9f9f9', transition: 'background 0.2s' }}
                             onMouseEnter={(e) => e.currentTarget.style.background = '#e8f5e9'}
                             onMouseLeave={(e) => e.currentTarget.style.background = '#f9f9f9'}>
                            <strong style={{ display: 'block', fontSize: '1.1em' }}>{empresa.nombre}</strong>
                            <span style={{ color: '#7f8c8d', fontSize: '0.9em' }}>NRC: {empresa.nrc}</span>
                        </div>
                    ))}
                </div>
            </>
        )}

        {/* --- PANTALLA CREAR EMPRESA --- */}
        {modoCrear && (
            <>
                <h2>🏢 Nueva Empresa</h2>
                <input placeholder="Nombre de la Empresa" value={nuevoNombre} onChange={e => setNuevoNombre(e.target.value)} style={{ display: 'block', width: '100%', padding: '10px', marginBottom: '10px' }} />
                <input placeholder="NRC" value={nuevoNrc} onChange={e => setNuevoNrc(e.target.value)} style={{ display: 'block', width: '100%', padding: '10px', marginBottom: '10px' }} />
                <input placeholder="NIT (Opcional)" value={nuevoNit} onChange={e => setNuevoNit(e.target.value)} style={{ display: 'block', width: '100%', padding: '10px', marginBottom: '10px' }} />
                
                <div style={{ marginBottom: '15px', textAlign: 'left' }}>
                    <label>
                        <input type="checkbox" checked={nuevoEsImportador} onChange={e => setNuevoEsImportador(e.target.checked)} />
                        {' '} Es Importador
                    </label>
                </div>

                <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                    <button onClick={() => setModoCrear(false)} style={{ padding: '10px 20px', background: 'transparent', color: '#e74c3c', border: '1px solid #e74c3c', borderRadius: '5px', cursor: 'pointer' }}>Cancelar</button>
                    <button onClick={guardarNuevaEmpresa} style={{ padding: '10px 20px', background: '#27ae60', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>Guardar</button>
                </div>
            </>
        )}
      </div>
    </div>
  );
};

export default SeleccionEmpresa;