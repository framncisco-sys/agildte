import React, { useState, useEffect } from 'react';

// --- CONFIGURACIÓN GLOBAL Y LISTAS ---
const tiposOperacion = [{ code: "1", label: "1 - Gravada" }, { code: "2", label: "2 - Exenta" }, { code: "3", label: "3 - No Sujeta" }, { code: "4", label: "4 - Mixta" }];
const tiposIngreso = [{ code: "1", label: "1 - Profesiones" }, { code: "2", label: "2 - Servicios" }, { code: "3", label: "3 - Comercial" }, { code: "4", label: "4 - Industrial" }];
const baseDatosProveedores = { "100-1": "ACME S.A.", "355524-3": "DENIS ALEXANDER" };
const baseDatosClientes = { "800-1": "CLIENTE EJEMPLO", "900-2": "JUAN PÉREZ" };
const datosAcciones = { "DEFAULT": { comprasRobot: 0, erroresDTE: 0, facturasPospuestas: 0 } };
const opcionesGasto = { "Gravada": ["Costo", "Gasto"], "Exenta": ["Costo", "Gasto"] };
const opcionesSector = { "Costo": ["Industria", "Comercio"], "Gasto": ["Admin", "Ventas"] };

// --- COMPONENTE DE LOGIN (SEGURIDAD) ---
function LoginScreen({ onLogin }) {
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    // 🔐 CREDENCIALES PROVISIONALES
    if (user === "admin" && pass === "1234") {
      onLogin(true);
    } else {
      setError("❌ Credenciales incorrectas");
    }
  };

  return (
    <div style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', backgroundColor: '#2c3e50' }}>
      <div style={{ background: 'white', padding: '40px', borderRadius: '10px', boxShadow: '0 10px 25px rgba(0,0,0,0.2)', width: '350px', textAlign: 'center' }}>
        <h1 style={{ color: '#2c3e50', marginBottom: '5px' }}>🔐 Acceso</h1>
        <p style={{ color: '#7f8c8d', marginBottom: '30px' }}>Sistema Contable SA</p>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '15px', textAlign: 'left' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', color: '#34495e' }}>Usuario</label>
            <input 
              type="text" 
              value={user} 
              onChange={(e) => setUser(e.target.value)} 
              style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #bdc3c7', boxSizing: 'border-box' }}
              placeholder="Ej: admin"
            />
          </div>
          <div style={{ marginBottom: '25px', textAlign: 'left' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', color: '#34495e' }}>Contraseña</label>
            <input 
              type="password" 
              value={pass} 
              onChange={(e) => setPass(e.target.value)} 
              style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #bdc3c7', boxSizing: 'border-box' }}
              placeholder="••••"
            />
          </div>
          {error && <div style={{ color: '#e74c3c', marginBottom: '15px', fontSize: '0.9em' }}>{error}</div>}
          <button type="submit" style={{ width: '100%', padding: '12px', background: '#27ae60', color: 'white', border: 'none', borderRadius: '5px', fontSize: '1.1em', cursor: 'pointer', fontWeight: 'bold' }}>Ingresar al Sistema</button>
        </form>
      </div>
    </div>
  );
}

function App() {
  // --- ESTADO DE SEGURIDAD ---
  const [estaLogueado, setEstaLogueado] = useState(false);

  // --- ESTADOS DE LA APP ---
  const [listaClientes, setListaClientes] = useState([]);
  const [clienteActivo, setClienteActivo] = useState(""); 
  const [periodo, setPeriodo] = useState("2025-10");
  const [mostrarModalCliente, setMostrarModalCliente] = useState(false);
  const [vistaActual, setVistaActual] = useState("dashboard");

  // Nuevo Cliente
  const [modoCrearCliente, setModoCrearCliente] = useState(false);
  const [nuevoNombre, setNuevoNombre] = useState("");
  const [nuevoNrc, setNuevoNrc] = useState("");
  const [nuevoNit, setNuevoNit] = useState("");
  const [nuevoEsImportador, setNuevoEsImportador] = useState(false);

  // Datos Financieros
  const [datosFiscales, setDatosFiscales] = useState({ ventasGravadas: 0, debitoFiscal: 0, comprasGravadas: 0, creditoFiscal: 0, retencionCliente1: 0, retencionTarjeta2: 0, percepcionesPagadas: 0 });
  const [listaCompras, setListaCompras] = useState([]);
  const [listaVentas, setListaVentas] = useState([]);
  const [cargaAnalisis, setCargaAnalisis] = useState({ compras: [], ventas: [], ignorados: [], retenciones: [], resumen: {total_iva_compras:0, total_iva_ventas:0} });
  const [seleccionados, setSeleccionados] = useState([]); 

  // Formulario Compras
  const [idEdicion, setIdEdicion] = useState(null);
  const [tipoDocumento, setTipoDocumento] = useState("03");
  const [fechaFactura, setFechaFactura] = useState("");
  const [alertaFecha, setAlertaFecha] = useState(null);
  const [nrcProveedor, setNrcProveedor] = useState("");
  const [nombreProveedor, setNombreProveedor] = useState("");
  const [numeroDocumento, setNumeroDocumento] = useState(""); 
  const [montoGravado, setMontoGravado] = useState("");
  const [montoIva, setMontoIva] = useState("");
  const [montoTotal, setMontoTotal] = useState("");
  const [clasif1, setClasif1] = useState("Gravada");
  const [clasif2, setClasif2] = useState("Gasto");
  const [clasif3, setClasif3] = useState(""); 

  // Formulario Ventas
  const [tipoVenta, setTipoVenta] = useState("CF");
  const [claseDocumento, setClaseDocumento] = useState("1");
  const [fechaVenta, setFechaVenta] = useState("");
  const [numDocumento, setNumDocumento] = useState(""); 
  const [serie, setSerie] = useState("");
  const [resolucion, setResolucion] = useState("");
  const [sello, setSello] = useState("");
  const [numControlDTE, setNumControlDTE] = useState("");
  const [numFormUnico, setNumFormUnico] = useState("");
  const [clienteReceptor, setClienteReceptor] = useState("");
  const [nrcReceptor, setNrcReceptor] = useState("");
  const [ventaGravada, setVentaGravada] = useState("");
  const [debitoFiscal, setDebitoFiscal] = useState("");
  const [ventaTotal, setVentaTotal] = useState("");
  const [delNum, setDelNum] = useState("");
  const [alNum, setAlNum] = useState("");
  const [opRenta, setOpRenta] = useState("1");
  const [ingresoTipo, setIngresoTipo] = useState("3");

  // Formulario Retenciones
  const [retTipo, setRetTipo] = useState("162"); 
  const [retFecha, setRetFecha] = useState("");
  const [retMontoSujeto, setRetMontoSujeto] = useState(""); 
  const [retMonto, setRetMonto] = useState("");             
  const [retNit, setRetNit] = useState("");                 
  const [retEmisor, setRetEmisor] = useState("");           
  const [retCodigo, setRetCodigo] = useState("");           
  const [retNumero, setRetNumero] = useState("");           

  // VARIABLES DERIVADAS
  const clienteInfo = listaClientes.find(c => c.nrc === clienteActivo);
  const datos = datosFiscales; 
  const totalCreditos = parseFloat(datos.creditoFiscal) + parseFloat(datos.percepcionesPagadas || 0) + parseFloat(datos.remanenteMesAnterior || 0) + parseFloat(datos.retencionCliente1) + parseFloat(datos.retencionTarjeta2);
  const impuestoPorPagar = parseFloat(datos.debitoFiscal) - totalCreditos;
  const esRemanente = impuestoPorPagar < 0;

  // --- FUNCIONES DE CARGA ---
  const cargarClientes = () => { fetch('https://backend-production-8f98.up.railway.app/api/clientes/api/clientes/').then(r=>r.json()).then(setListaClientes).catch(console.error); };
  
  // Efectos solo se ejecutan si está logueado
  useEffect(() => { if(estaLogueado) cargarClientes(); }, [estaLogueado]);
  useEffect(() => { if (estaLogueado && clienteActivo && periodo) fetch(`https://backend-production-8f98.up.railway.app/api/clientes/api/finanzas/resumen/?nrc=${clienteActivo}&periodo=${periodo}`).then(r=>r.json()).then(setDatosFiscales); }, [estaLogueado, clienteActivo, periodo, vistaActual]);
  useEffect(() => { if (estaLogueado && vistaActual === "libroCompras" && clienteActivo) fetch(`https://backend-production-8f98.up.railway.app/api/clientes/api/compras/listar/?nrc=${clienteActivo}&periodo=${periodo}`).then(r=>r.json()).then(setListaCompras); }, [estaLogueado, vistaActual, clienteActivo, periodo]); 
  useEffect(() => { if (estaLogueado && (vistaActual === "libroVentasCCF" || vistaActual === "libroVentasCF") && clienteActivo) { const tipo = vistaActual === "libroVentasCCF" ? "CCF" : "CF"; fetch(`https://backend-production-8f98.up.railway.app/api/clientes/api/ventas/listar/?nrc=${clienteActivo}&periodo=${periodo}&tipo=${tipo}`).then(r=>r.json()).then(setListaVentas); } }, [estaLogueado, vistaActual, clienteActivo, periodo]);

  // --- LOGICA GENERAL ---
  const seleccionarCliente = (nrc) => { setClienteActivo(nrc); setMostrarModalCliente(false); setVistaActual("dashboard"); resetFormularios(); };

  const resetFormularios = () => {
      setIdEdicion(null); setTipoDocumento("03"); setFechaFactura(""); setAlertaFecha(null);
      setNrcProveedor(""); setNombreProveedor(""); setNumeroDocumento(""); 
      setMontoGravado(""); setMontoIva(""); setMontoTotal("");
      setTipoVenta("CF"); setFechaVenta(""); setDelNum(""); setAlNum("");
      setNumDocumento(""); setClienteReceptor(""); setNrcReceptor("");
      setVentaGravada(""); setDebitoFiscal(""); setVentaTotal("");
      setOpRenta("1"); setIngresoTipo("3"); setNumFormUnico("");
      setRetTipo("162"); setRetFecha(""); setRetMontoSujeto(""); setRetMonto(""); 
      setRetNit(""); setRetEmisor(""); setRetCodigo(""); setRetNumero("");
      setCargaAnalisis({ compras: [], ventas: [], ignorados: [], retenciones: [], resumen: {total_iva_compras:0, total_iva_ventas:0} });
      setSeleccionados([]); 
  };

  const guardarNuevoCliente = () => {
      if(!nuevoNombre || !nuevoNrc) { alert("Datos incompletos"); return; }
      fetch('https://backend-production-8f98.up.railway.app/api/clientes/api/clientes/crear/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nombre: nuevoNombre, nrc: nuevoNrc, nit: nuevoNit, es_importador: nuevoEsImportador }) })
      .then(async res => { if(res.ok) { alert("✅ Cliente Creado"); cargarClientes(); setModoCrearCliente(false); setNuevoNombre(""); setNuevoNrc(""); setNuevoNit(""); setNuevoEsImportador(false); } else alert("❌ Error: NRC duplicado."); });
  };

  // --- HANDLERS DE INPUTS ---
  const handleNrcChange = (e) => { const nrc = e.target.value; setNrcProveedor(nrc); if (baseDatosProveedores[nrc]) setNombreProveedor(baseDatosProveedores[nrc]); };
  const handleMontoChange = (e) => { const gravado = parseFloat(e.target.value); setMontoGravado(e.target.value); if (!isNaN(gravado)) { const iva = parseFloat((gravado * 0.13).toFixed(2)); setMontoIva(iva); setMontoTotal((gravado + iva).toFixed(2)); } else { setMontoIva(""); setMontoTotal(""); } };
  const validarFecha = (fecha) => { setFechaFactura(fecha); if (!fecha) return; const fechaDoc = new Date(fecha); const [anioP, mesP] = periodo.split("-"); const fechaPeriodo = new Date(anioP, mesP - 1, 1); const diffDays = Math.ceil(Math.abs(fechaPeriodo - fechaDoc) / (1000 * 60 * 60 * 24)); if (diffDays > 90 && fechaDoc < fechaPeriodo) setAlertaFecha("⚠️ ¡ALERTA! Excede 3 meses."); else setAlertaFecha(null); };
  const handleNrcVentaChange = (e) => { const nrc = e.target.value; setNrcReceptor(nrc); if (baseDatosClientes[nrc]) setClienteReceptor(baseDatosClientes[nrc]); };
  const handleVentaInput = (e) => {
      const valorInput = parseFloat(e.target.value);
      if (isNaN(valorInput)) { setVentaGravada(""); setDebitoFiscal(""); setVentaTotal(""); return; }
      const esExenta = ["2", "3", "13"].includes(opRenta);
      if (esExenta) { setVentaGravada(valorInput.toFixed(2)); setDebitoFiscal("0.00"); setVentaTotal(valorInput.toFixed(2)); return; }
      if (tipoVenta === "CF") { setVentaTotal(valorInput); const gravado = valorInput / 1.13; setVentaGravada(gravado.toFixed(2)); setDebitoFiscal((valorInput - gravado).toFixed(2)); } 
      else { setVentaGravada(valorInput); const iva = valorInput * 0.13; setDebitoFiscal(iva.toFixed(2)); setVentaTotal((valorInput + iva).toFixed(2)); }
  };

  const toggleSeleccion = (id) => { if (seleccionados.includes(id)) { setSeleccionados(seleccionados.filter(s => s !== id)); } else { setSeleccionados([...seleccionados, id]); } };

  // --- GUARDADO EN BACKEND ---
  const guardarCompraEnBackend = (irALibro) => {
    if (!fechaFactura || !nrcProveedor || !montoTotal) { alert("⚠️ Faltan datos."); return; }
    const paquete = { cliente: clienteActivo, fecha_emision: fechaFactura, tipo_documento: tipoDocumento, codigo_generacion: numeroDocumento, nrc_proveedor: nrcProveedor, nombre_proveedor: nombreProveedor, monto_gravado: montoGravado || 0, monto_iva: montoIva || 0, monto_total: montoTotal || 0, clasificacion_1: clasif1, clasificacion_2: clasif2, clasificacion_3: clasif3, periodo_aplicado: periodo, estado: "Registrado" };
    let url = 'https://backend-production-8f98.up.railway.app/api/clientes/api/compras/crear/'; let metodo = 'POST';
    if (idEdicion) { url = `https://backend-production-8f98.up.railway.app/api/clientes/api/compras/actualizar/${idEdicion}/`; metodo = 'PUT'; }
    fetch(url, { method: metodo, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(paquete) }).then(async res => { const data = await res.json(); if (res.ok) { alert("✅ Guardado"); if (irALibro) setVistaActual("libroCompras"); resetFormularios(); } else alert(data.error || "Error"); }).catch(console.error);
  };

  const guardarVentaEnBackend = () => {
      if (!fechaVenta || (!ventaGravada && !ventaTotal)) { alert("⚠️ Faltan datos básicos."); return; }
      const paqueteVenta = { cliente: clienteActivo, fecha_emision: fechaVenta, periodo_aplicado: periodo, tipo_venta: tipoVenta, clase_documento: claseDocumento, numero_documento: numDocumento || delNum, numero_control_desde: tipoVenta === 'CF' ? delNum : null, numero_control_hasta: tipoVenta === 'CF' ? alNum : null, serie_documento: serie, numero_resolucion: resolucion, sello_recepcion: sello, numero_control_dte: numControlDTE, numero_formulario_unico: numFormUnico, nombre_receptor: tipoVenta === 'CCF' ? clienteReceptor : null, nrc_receptor: tipoVenta === 'CCF' ? nrcReceptor : null, venta_gravada: ventaGravada || 0, debito_fiscal: debitoFiscal || 0, clasificacion_venta: opRenta, tipo_ingreso: ingresoTipo };
      fetch('https://backend-production-8f98.up.railway.app/api/clientes/api/ventas/crear/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(paqueteVenta) }).then(async res => { if (res.ok) { alert("✅ ¡Venta Registrada!"); resetFormularios(); setVistaActual(tipoVenta === 'CCF' ? "libroVentasCCF" : "libroVentasCF"); } else alert("❌ Error al guardar venta."); }).catch(console.error);
  };

  const guardarRetencionEnBackend = () => {
      if (!retFecha || !retMonto || !retNit) { alert("⚠️ Faltan datos."); return; }
      const paqueteRet = { cliente: clienteActivo, periodo_aplicado: periodo, fecha_emision: retFecha, tipo_retencion: retTipo, monto_retenido: retMonto, monto_sujeto: retMontoSujeto, nit_emisor: retNit, nombre_emisor: retEmisor, codigo_generacion: retCodigo, numero_documento: retNumero };
      fetch('https://backend-production-8f98.up.railway.app/api/clientes/api/retenciones/crear/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(paqueteRet) }).then(async res => { if (res.ok) { alert("✅ Retención Agregada"); resetFormularios(); setVistaActual("dashboard"); } else alert("❌ Error al guardar retención."); });
  };

  const cargarParaEditar = (compra) => { setIdEdicion(compra.id); setTipoDocumento(compra.tipo_documento); setFechaFactura(compra.fecha_emision); setNumeroDocumento(compra.codigo_generacion); setNrcProveedor(compra.nrc_proveedor); setNombreProveedor(compra.nombre_proveedor); setMontoGravado(compra.monto_gravado); setMontoIva(compra.monto_iva); setMontoTotal(compra.monto_total); setClasif1(compra.clasificacion_1); setClasif2(compra.clasificacion_2); setClasif3(compra.clasificacion_3); setVistaActual("nuevaCompra"); };
  const cargarVentaParaEditar = (venta) => { setIdEdicion(venta.id); setTipoVenta(venta.tipo_venta); setFechaVenta(venta.fecha_emision); setClaseDocumento(venta.clase_documento); setNumDocumento(venta.numero_documento); setDelNum(venta.numero_control_desde); setAlNum(venta.numero_control_hasta); setSerie(venta.serie_documento); setResolucion(venta.numero_resolucion); setSello(venta.sello_recepcion); setNumControlDTE(venta.numero_control_dte); setNumFormUnico(venta.numero_formulario_unico); setClienteReceptor(venta.nombre_receptor); setNrcReceptor(venta.nrc_receptor); setVentaGravada(venta.venta_gravada); setDebitoFiscal(venta.debito_fiscal); setVentaTotal((parseFloat(venta.venta_gravada) + parseFloat(venta.debito_fiscal)).toFixed(2)); setOpRenta(venta.clasificacion_venta); setIngresoTipo(venta.tipo_ingreso); setVistaActual("nuevaVenta"); };
  const borrarSeleccionados = (tipo) => { if (seleccionados.length === 0) return; if (window.confirm(`⚠️ ¿Eliminar ${seleccionados.length} items?`)) { const promesas = seleccionados.map(id => fetch(`https://backend-production-8f98.up.railway.app/api/clientes/api/${tipo}/borrar/${id}/`, { method: 'DELETE' })); Promise.all(promesas).then(() => { alert("🗑️ Eliminados."); setSeleccionados([]); if (tipo === 'compras') fetch(`https://backend-production-8f98.up.railway.app/api/clientes/api/compras/listar/?nrc=${clienteActivo}&periodo=${periodo}`).then(r=>r.json()).then(setListaCompras); else { const tipoV = vistaActual === "libroVentasCCF" ? "CCF" : "CF"; fetch(`https://backend-production-8f98.up.railway.app/api/clientes/api/ventas/listar/?nrc=${clienteActivo}&periodo=${periodo}&tipo=${tipoV}`).then(r=>r.json()).then(setListaVentas); } fetch(`https://backend-production-8f98.up.railway.app/api/clientes/api/finanzas/resumen/?nrc=${clienteActivo}&periodo=${periodo}`).then(r=>r.json()).then(setDatosFiscales); }); } };
  const handleEditarSeleccion = (tipoLibro) => { const id = seleccionados[0]; if (tipoLibro === 'compras') { const item = listaCompras.find(i => i.id === id); if(item) cargarParaEditar(item); } else { const item = listaVentas.find(i => i.id === id); if(item) cargarVentaParaEditar(item); } };

  // --- VIGILANTE: SI NO ESTÁ LOGUEADO, MOSTRAR LOGIN ---
  if (!estaLogueado) {
    return <LoginScreen onLogin={setEstaLogueado} />;
  }

  // --- SI ESTÁ LOGUEADO, MOSTRAR LA APP COMPLETA ---
  return (
    <div style={{ padding: '20px', fontFamily: 'Segoe UI, sans-serif', backgroundColor: '#f4f7f6', minHeight: '100vh' }}>
      <header style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
           <div style={{display: 'flex', alignItems: 'center', gap: '15px'}}>
               <h1 style={{ color: '#2c3e50', margin: 0, cursor: 'pointer' }} onClick={() => setVistaActual("dashboard")}>📊 Sistema Contable SA</h1>
               <span style={{fontSize: '0.8em', color: '#95a5a6'}}>| Usuario: Admin</span>
           </div>
           <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {clienteActivo && <span style={{color: '#27ae60', fontWeight: 'bold', fontSize: '1.2em'}}>{clienteInfo?.nombre}</span>}
              <button onClick={() => setMostrarModalCliente(true)} style={{padding: '10px 20px', background: '#2c3e50', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold'}}>{clienteActivo ? "🔄 Cambiar" : "👤 Seleccionar"}</button>
              <button onClick={() => { if(window.confirm("¿Cerrar Sesión?")) setEstaLogueado(false); }} style={{padding: '10px', background: '#c0392b', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', marginLeft: '10px'}}>🔒 Salir</button>
           </div>
        </div>
      </header>

      {mostrarModalCliente && (
        <div style={{position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000}}>
          <div style={{backgroundColor: 'white', padding: '30px', borderRadius: '10px', width: '500px', maxWidth: '95%'}}>
            <h2 style={{marginTop: 0}}>Selecciona una Empresa</h2>
            {
               !modoCrearCliente ? (
                <>
                   <div style={{display:'flex', justifyContent:'flex-end', marginBottom:'10px'}}>
                       <button onClick={()=>setModoCrearCliente(true)} style={{background:'#27ae60', color:'white', border:'none', padding:'8px', borderRadius:'5px', cursor:'pointer'}}>➕ Nueva Empresa</button>
                   </div>
                   <div style={{display: 'flex', flexDirection: 'column', gap: '10px', maxHeight:'300px', overflowY:'auto'}}>
                    {listaClientes.map(cliente => (
                        <button key={cliente.nrc} onClick={() => { if(window.confirm(`¿Cambiar a ${cliente.nombre}?`)) seleccionarCliente(cliente.nrc); }} style={{padding: '15px', textAlign: 'left', border: '1px solid #eee', borderRadius: '8px', background: '#f9f9f9', cursor: 'pointer', fontSize: '1em'}}><strong>{cliente.nombre}</strong> {cliente.es_importador && <span style={{background: '#3498db', color: 'white', fontSize: '0.7em', padding: '2px 5px', borderRadius: '4px', marginLeft: '5px'}}>IMPORTADOR</span>}<br/><small style={{color: '#7f8c8d'}}>NRC: {cliente.nrc}</small></button>
                    ))}
                   </div>
                   <button onClick={() => setMostrarModalCliente(false)} style={{marginTop: '20px', width: '100%', padding: '10px', border: 'none', background: 'transparent', color: '#c0392b', cursor: 'pointer'}}>Cancelar</button>
                </>
               ) : (
                <>
                    <h3>Nueva Empresa</h3>
                    <div style={{marginBottom:'10px'}}><label style={{display:'block'}}>Nombre / Razón Social</label><input value={nuevoNombre} onChange={(e)=>setNuevoNombre(e.target.value)} style={{width:'100%', padding:'8px'}} /></div>
                    <div style={{marginBottom:'10px'}}><label style={{display:'block'}}>NRC (Sin Guiones)</label><input value={nuevoNrc} onChange={(e)=>setNuevoNrc(e.target.value)} style={{width:'100%', padding:'8px'}} /></div>
                    <div style={{marginBottom:'10px'}}><label style={{display:'block'}}>NIT</label><input value={nuevoNit} onChange={(e)=>setNuevoNit(e.target.value)} style={{width:'100%', padding:'8px'}} /></div>
                    <div style={{marginBottom:'20px'}}><label><input type="checkbox" checked={nuevoEsImportador} onChange={(e)=>setNuevoEsImportador(e.target.checked)} /> Es Importador</label></div>
                    <div style={{display:'flex', gap:'10px'}}>
                        <button onClick={guardarNuevoCliente} style={{flex:1, padding:'10px', background:'#27ae60', color:'white', border:'none', borderRadius:'5px', cursor:'pointer'}}>Guardar</button>
                        <button onClick={()=>setModoCrearCliente(false)} style={{flex:1, padding:'10px', background:'#95a5a6', color:'white', border:'none', borderRadius:'5px', cursor:'pointer'}}>Cancelar</button>
                    </div>
                </>
               )
            }
          </div>
        </div>
      )}

      <main>
        {!clienteActivo ? (
          <div style={{textAlign: 'center', color: '#7f8c8d', marginTop: '100px'}}><h2>👋 ¡Bienvenido!</h2><p>Selecciona una empresa para conectar.</p></div>
        ) : (
          <>
            {vistaActual === "dashboard" && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div style={{ background: 'white', padding: '20px', borderRadius: '10px', borderLeft: '5px solid #f39c12', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
                    <h2 style={{ margin: '0 0 10px 0', color: '#e67e22' }}>🔔 Acciones</h2>
                    <p style={{color: 'green'}}>✅ Todo al día</p>
                    <button onClick={() => setVistaActual("cargaMasiva")} style={{ background: '#f39c12', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '5px', cursor: 'pointer' }}>🤖 Carga Masiva</button>
                  </div>
                  <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
                    <h2 style={{ margin: '0 0 15px 0', color: '#2c3e50' }}>🚀 Accesos Rápidos</h2>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                      <button onClick={() => setVistaActual("nuevaCompra")} style={{ flex: '1', padding: '15px', background: '#3498db', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>➕ Compra</button>
                      <button onClick={() => setVistaActual("nuevaVenta")} style={{ flex: '1', padding: '15px', background: '#9b59b6', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>➕ Venta</button>
                      <button onClick={() => setVistaActual("nuevaRetencion")} style={{ flex: '1', padding: '15px', background: '#27ae60', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>💰 Retención</button>
                      <button onClick={() => setVistaActual("libroCompras")} style={{ flex: '1', padding: '15px', background: '#34495e', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>📚 Compras</button>
                      <button onClick={() => setVistaActual("libroVentasCCF")} style={{ flex: '1', padding: '15px', background: '#8e44ad', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>🛒 Ventas CCF</button>
                      <button onClick={() => setVistaActual("libroVentasCF")} style={{ flex: '1', padding: '15px', background: '#9b59b6', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>🧾 Ventas CF</button>
                    </div>
                  </div>
                </div>
                <div style={{ background: 'white', padding: '20px', borderRadius: '10px', borderTop: '5px solid #27ae60', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
                    <div style={{display:'flex', justifyContent:'space-between'}}><h2 style={{color: '#27ae60', margin: 0}}>💰 Resumen Fiscal</h2><select value={periodo} onChange={(e) => setPeriodo(e.target.value)} style={{padding:'5px', border:'1px solid #ccc', borderRadius:'5px'}}><option value="2025-09">Sep 2025</option><option value="2025-10">Oct 2025</option><option value="2025-11">Nov 2025</option></select></div>
                    <div style={{ marginBottom: '20px', marginTop: '20px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.1em', marginBottom: '5px' }}><span>(+) Débito Fiscal:</span><strong>${parseFloat(datos.debitoFiscal).toFixed(2)}</strong></div>
                    </div>
                    <div style={{ background: '#f9f9f9', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
                        <h4 style={{margin: '0 0 10px 0', color: '#7f8c8d'}}>(-) Créditos y Pagos</h4>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', color: '#c0392b' }}><span>Crédito Fiscal:</span><span>${parseFloat(datos.creditoFiscal).toFixed(2)}</span></div>
                        {datos.retencionCliente1 > 0 && <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', color: '#27ae60' }}><span>Retención 1% (Clientes):</span><span>${parseFloat(datos.retencionCliente1).toFixed(2)}</span></div>}
                        {datos.retencionTarjeta2 > 0 && <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', color: '#27ae60' }}><span>Retención Tarjetas:</span><span>${parseFloat(datos.retencionTarjeta2).toFixed(2)}</span></div>}
                        {datos.percepcionesPagadas > 0 && <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', color: '#27ae60' }}><span>Percepción 1%:</span><span>${parseFloat(datos.percepcionesPagadas).toFixed(2)}</span></div>}
                    </div>
                    <h1>${Math.abs(impuestoPorPagar).toFixed(2)} {esRemanente ? " (Remanente)" : " (A Pagar)"}</h1>

                    {/* CENTRO DE REPORTES */}
                    <div style={{ background: '#fcfcfc', padding: '15px', borderRadius: '10px', marginTop:'20px', border:'1px solid #eee' }}>
                        <h4 style={{marginTop:0, color:'#34495e'}}>📥 Centro de Reportes (CSV MH)</h4>
                        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'10px'}}>
                             <button onClick={() => window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/csv-compras/?nrc=${clienteActivo}&periodo=${periodo}`} style={{padding:'8px', background:'#eee', border:'none', cursor:'pointer'}}>Compras</button>
                             <button onClick={() => window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/csv-ventas-ccf/?nrc=${clienteActivo}&periodo=${periodo}`} style={{padding:'8px', background:'#eee', border:'none', cursor:'pointer'}}>Ventas CCF</button>
                             <button onClick={() => window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/csv-ventas-cf/?nrc=${clienteActivo}&periodo=${periodo}`} style={{padding:'8px', background:'#eee', border:'none', cursor:'pointer'}}>Ventas CF</button>
                             <button onClick={() => window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/csv-163/?nrc=${clienteActivo}&periodo=${periodo}`} style={{padding:'8px', background:'#eee', border:'none', cursor:'pointer'}}>Percepciones (163)</button>
                             <button onClick={() => window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/csv-162/?nrc=${clienteActivo}&periodo=${periodo}`} style={{padding:'8px', background:'#eee', border:'none', cursor:'pointer'}}>Retención 1% (162)</button>
                             <button onClick={() => window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/csv-161/?nrc=${clienteActivo}&periodo=${periodo}`} style={{padding:'8px', background:'#eee', border:'none', cursor:'pointer'}}>Retención TC (161)</button>
                        </div>
                    </div>
                </div>
              </div>
            )}

            {vistaActual === "bandeja" && <div style={{padding:'20px'}}><button onClick={()=>setVistaActual("dashboard")}>⬅️ Volver</button><h2>📥 Bandeja</h2><p>Conectando al robot...</p></div>}
            
            {/* --- VISTA: NUEVA COMPRA --- */}
            {vistaActual === "nuevaCompra" && (
              <div style={{ background: 'white', padding: '30px', borderRadius: '10px', maxWidth: '800px', margin: '0 auto', boxShadow: '0 4px 10px rgba(0,0,0,0.1)' }}>
                  <div style={{display: 'flex', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #eee', paddingBottom: '10px'}}>
                   <button onClick={() => setVistaActual("dashboard")} style={{marginRight: '15px', cursor: 'pointer', border: 'none', background: 'transparent', fontSize: '1.5em'}}>⬅️</button>
                   <h2 style={{margin: 0, color: idEdicion ? '#f39c12' : '#3498db'}}>{idEdicion ? `✏️ Editando Compra` : '📝 Registrar Nueva Compra'}</h2>
                 </div>
                 <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px'}}>
                     <div><label style={{display: 'block'}}>Tipo</label><select value={tipoDocumento} onChange={(e) => setTipoDocumento(e.target.value)} style={{width: '100%', padding: '10px'}}><option value="03">03 - CCF</option><option value="05">05 - NC</option><option value="14">14 - FSE</option>{clienteInfo?.es_importador && <option value="12">12 - Importación</option>}</select></div>
                     <div><label style={{display: 'block'}}>Fecha</label><input type="date" value={fechaFactura} onChange={(e) => validarFecha(e.target.value)} style={{width: '100%', padding: '8px', border: alertaFecha ? '2px solid red' : '1px solid #ccc'}} />{alertaFecha && <small style={{color:'red'}}>{alertaFecha}</small>}</div>
                 </div>
                 <div style={{marginBottom: '20px'}}><label style={{display: 'block'}}>Nº Doc</label><input value={numeroDocumento} onChange={(e) => setNumeroDocumento(e.target.value)} style={{width: '100%', padding: '10px', border: '1px solid #ccc'}} /></div>
                 <div style={{marginBottom: '20px'}}><input placeholder="NRC Prov" value={nrcProveedor} onChange={handleNrcChange} style={{padding:'10px', marginRight:'10px'}} /><input placeholder="Nombre" value={nombreProveedor} onChange={(e)=>setNombreProveedor(e.target.value)} style={{padding:'10px', width:'300px'}} /></div>
                 <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '20px'}}>
                     <input type="number" placeholder="Gravado" value={montoGravado} onChange={handleMontoChange} style={{padding:'10px'}} />
                     <input type="number" placeholder="IVA" value={montoIva} readOnly style={{padding:'10px', background:'#eee'}} />
                     <input type="number" placeholder="Total" value={montoTotal} readOnly style={{padding:'10px', background:'#eee'}} />
                 </div>
                 <div style={{display: 'flex', gap: '10px'}}>
                      <select value={clasif1} onChange={(e) => {setClasif1(e.target.value); setClasif2("");}} style={{flex:1, padding:'10px'}}>{Object.keys(opcionesGasto).map(op=><option key={op}>{op}</option>)}</select>
                      <select value={clasif2} onChange={(e) => {setClasif2(e.target.value); setClasif3("");}} disabled={!clasif1} style={{flex:1, padding:'10px'}}><option value="">--</option>{clasif1 && opcionesGasto[clasif1]?.map(op=><option key={op}>{op}</option>)}</select>
                      <select value={clasif3} onChange={(e) => setClasif3(e.target.value)} disabled={!clasif2} style={{flex:1, padding:'10px'}}><option value="">--</option>{clasif2 && opcionesSector[clasif2]?.map(op=><option key={op}>{op}</option>)}</select>
                 </div>
                 <div style={{marginTop: '30px', display: 'flex', justifyContent: 'flex-end', gap: '10px'}}>
                     <button onClick={() => guardarCompraEnBackend(false)} style={{padding: '15px 20px', background: '#34495e', color: 'white', border: 'none', borderRadius: '5px', fontSize: '1em', cursor: 'pointer', fontWeight: 'bold'}}>{idEdicion ? "💾 Guardar Cambios" : "➕ Guardar y Agregar Otra"}</button>
                     <button onClick={() => guardarCompraEnBackend(true)} style={{padding: '15px 30px', background: '#27ae60', color: 'white', border: 'none', borderRadius: '5px', fontSize: '1em', cursor: 'pointer', fontWeight: 'bold'}}>{idEdicion ? "💾 Guardar y Salir" : "💾 Guardar y Terminar"}</button>
                 </div>
               </div>
            )}

            {/* --- VISTA: LIBRO DE COMPRAS --- */}
            {vistaActual === "libroCompras" && (
                <div style={{ background: 'white', padding: '20px', borderRadius: '10px' }}>
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                        <div style={{display:'flex', alignItems:'center'}}><button onClick={() => setVistaActual("dashboard")}>⬅️</button><h2 style={{margin:0, marginLeft:'10px'}}>📚 Libro Compras</h2></div>
                        {seleccionados.length > 0 && (
                            <div style={{display:'flex', gap:'10px'}}>
                                {seleccionados.length === 1 && <button onClick={() => handleEditarSeleccion('compras')} style={{background:'#f39c12', color:'white', border:'none', padding:'10px 20px', borderRadius:'5px', cursor:'pointer'}}>✏️ Editar</button>}
                                <button onClick={() => borrarSeleccionados('compras')} style={{background:'#c0392b', color:'white', border:'none', padding:'10px 20px', borderRadius:'5px', cursor:'pointer'}}>🗑️ Borrar ({seleccionados.length})</button>
                            </div>
                        )}
                    </div>
                    <div style={{display:'flex', gap:'10px', marginBottom:'20px'}}>
                         <button onClick={() => { window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/csv-compras/?nrc=${clienteActivo}&periodo=${periodo}`; }} style={{ padding: '10px', background: '#7f8c8d', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>📄 Descargar CSV Compras</button>
                         <button onClick={() => { window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/pdf-compras/?nrc=${clienteActivo}&periodo=${periodo}`; }} style={{ padding: '10px', background: '#e74c3c', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>🖨️ Imprimir PDF</button>
                    </div>
                    <table style={{width:'100%', borderCollapse:'collapse'}}>
                        <thead><tr style={{background:'#34495e', color:'white'}}><th style={{padding:'10px'}}>Select</th><th>Fecha</th><th>Nº Doc</th><th>Proveedor</th><th>Total</th></tr></thead>
                        <tbody>
                            {listaCompras.map(compra => (
                                <tr key={compra.id} style={{borderBottom:'1px solid #eee'}}>
                                    <td style={{textAlign:'center'}}><input type="checkbox" onChange={() => toggleSeleccion(compra.id)} checked={seleccionados.includes(compra.id)} /></td>
                                    <td>{compra.fecha_emision}</td><td>{compra.codigo_generacion}</td><td>{compra.nombre_proveedor}</td><td style={{textAlign:'right'}}>${parseFloat(compra.monto_total).toFixed(2)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {(vistaActual === "libroVentasCCF" || vistaActual === "libroVentasCF") && (
                <div style={{ background: 'white', padding: '20px', borderRadius: '10px' }}>
                      <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                        <div style={{display:'flex', alignItems:'center'}}>
                            <button onClick={() => setVistaActual("dashboard")}>⬅️</button>
                            <h2 style={{margin:0, marginLeft:'10px'}}>{vistaActual === "libroVentasCCF" ? "🛒 Ventas CCF" : "🧾 Ventas Consumidor Final"}</h2>
                        </div>
                        {seleccionados.length > 0 && (
                            <div style={{display:'flex', gap:'10px'}}>
                                {seleccionados.length === 1 && <button onClick={() => handleEditarSeleccion('ventas')} style={{background:'#f39c12', color:'white', border:'none', padding:'10px 20px', borderRadius:'5px', cursor:'pointer'}}>✏️ Editar</button>}
                                <button onClick={() => borrarSeleccionados('ventas')} style={{background:'#c0392b', color:'white', border:'none', padding:'10px 20px', borderRadius:'5px', cursor:'pointer'}}>🗑️ Borrar ({seleccionados.length})</button>
                            </div>
                        )}
                    </div>
                    <div style={{display:'flex', gap:'10px', marginBottom:'20px'}}>
                         <button onClick={() => window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/csv-ventas-${vistaActual === "libroVentasCCF" ? 'ccf' : 'cf'}/?nrc=${clienteActivo}&periodo=${periodo}`} style={{ padding: '10px', background: '#9b59b6', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>📄 Descargar CSV MH</button>
                         {vistaActual === "libroVentasCCF" && <button onClick={() => window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/pdf-ventas-ccf/?nrc=${clienteActivo}&periodo=${periodo}`} style={{ padding: '10px', background: '#e74c3c', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>🖨️ PDF CCF</button>}
                         {vistaActual === "libroVentasCF" && <button onClick={() => window.location.href = `https://backend-production-8f98.up.railway.app/api/clientes/api/reportes/pdf-ventas-cf/?nrc=${clienteActivo}&periodo=${periodo}`} style={{ padding: '10px', background: '#e74c3c', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>🖨️ PDF CF</button>}
                    </div>
                    <table style={{width:'100%', borderCollapse:'collapse'}}>
                        <thead><tr style={{background:'#8e44ad', color:'white'}}><th style={{padding:'10px'}}>Select</th><th>Fecha</th><th>Documento</th><th>Total</th><th>Débito</th></tr></thead>
                        <tbody>
                            {listaVentas.map(v => (
                                <tr key={v.id} style={{borderBottom:'1px solid #eee'}}>
                                    <td style={{textAlign:'center'}}><input type="checkbox" onChange={() => toggleSeleccion(v.id)} checked={seleccionados.includes(v.id)} /></td>
                                    <td>{v.fecha_emision}</td>
                                    <td>{v.tipo_venta === 'CCF' ? v.numero_documento : `${v.numero_control_desde}-${v.numero_control_hasta}`}</td>
                                    <td style={{textAlign:'right'}}>${(parseFloat(v.venta_gravada)+parseFloat(v.debito_fiscal)).toFixed(2)}</td>
                                    <td style={{textAlign:'right'}}>${parseFloat(v.debito_fiscal).toFixed(2)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* --- VISTA: ADUANA DE DATOS (CARGA MASIVA) --- */}
            {vistaActual === "cargaMasiva" && (
              <div style={{ background: 'white', padding: '30px', borderRadius: '10px', maxWidth: '1200px', margin: '0 auto' }}>
                 <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px'}}>
                    <h2 style={{margin:0, color: '#2c3e50'}}>🛃 Aduana de Documentos</h2>
                    <button onClick={() => setVistaActual("dashboard")} style={{background:'transparent', border:'none', fontSize:'1.5em', cursor:'pointer'}}>❌</button>
                 </div>
                 {cargaAnalisis.compras.length === 0 && cargaAnalisis.ventas.length === 0 && cargaAnalisis.ignorados.length === 0 ? (
                     <div style={{border: '3px dashed #3498db', padding: '50px', textAlign:'center', borderRadius: '15px', backgroundColor: '#f0f8ff', cursor: 'pointer', position: 'relative'}}>
                        <span style={{fontSize: '3em'}}>📂</span>
                        <p style={{fontWeight: 'bold', color: '#2980b9'}}>Arrastra tus JSON aquí para analizarlos</p>
                        <input type="file" multiple accept=".json"
                            onChange={(e) => {
                                const formData = new FormData();
                                formData.append('nrc_activo', clienteActivo);
                                Array.from(e.target.files).forEach(file => formData.append('archivos', file));
                                fetch('https://backend-production-8f98.up.railway.app/api/clientes/api/sistema/procesar-lote/', { method: 'POST', body: formData }).then(r => r.json()).then(data => setCargaAnalisis(data)).catch(err => alert("Error analizando"));
                                e.target.value = null; 
                            }}
                            style={{opacity: 0, position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', cursor: 'pointer'}} 
                        />
                     </div>
                 ) : (
                     <div>
                         <div style={{display:'flex', gap:'10px', marginBottom:'20px'}}>
                             <div style={{background:'#e8f8f5', padding:'10px', borderRadius:'5px', flex:1}}>🛒 Compras: <strong>{cargaAnalisis.compras.length}</strong></div>
                             <div style={{background:'#e8eaf6', padding:'10px', borderRadius:'5px', flex:1}}>📈 Ventas: <strong>{cargaAnalisis.ventas.length}</strong></div>
                             <div style={{background:'#ffebee', padding:'10px', borderRadius:'5px', flex:1}}>🗑️ Ignorados: <strong>{cargaAnalisis.ignorados.length}</strong></div>
                         </div>
                         {cargaAnalisis.compras.length > 0 && (
                             <div style={{marginBottom:'30px'}}>
                                 <h3 style={{color:'#27ae60'}}>🛒 Compras</h3>
                                 <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.85em'}}>
                                     <thead style={{background:'#27ae60', color:'white'}}><tr><th style={{padding:'8px'}}>Fecha</th><th>Proveedor</th><th>Total</th><th>IVA</th><th>Clasificación 1</th><th>Clasificación 2</th></tr></thead>
                                     <tbody>
                                         {cargaAnalisis.compras.map((c, i) => (
                                             <tr key={i} style={{borderBottom:'1px solid #eee'}}>
                                                 <td style={{padding:'8px'}}>{c.fecha}</td><td>{c.emisor_nombre}</td><td style={{fontWeight:'bold'}}>${c.total.toFixed(2)}</td><td style={{color: c.iva > 0 ? 'black' : 'red'}}>${c.iva.toFixed(2)}</td>
                                                 <td><select value={c.clasificacion_1} onChange={(e) => { const nc = [...cargaAnalisis.compras]; nc[i].clasificacion_1 = e.target.value; setCargaAnalisis({...cargaAnalisis, compras: nc}); }} style={{padding:'5px', width:'100%'}}><option>Gravada</option><option>Exenta</option></select></td>
                                                 <td><select value={c.clasificacion_2} onChange={(e) => { const nc = [...cargaAnalisis.compras]; nc[i].clasificacion_2 = e.target.value; setCargaAnalisis({...cargaAnalisis, compras: nc}); }} style={{padding:'5px', width:'100%'}}><option>Gasto</option><option>Costo</option></select></td>
                                             </tr>
                                         ))}
                                     </tbody>
                                 </table>
                             </div>
                         )}
                         {cargaAnalisis.ventas.length > 0 && (
                             <div style={{marginBottom:'30px'}}>
                                 <h3 style={{color:'#9b59b6'}}>📈 Ventas</h3>
                                 <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.85em'}}>
                                     <thead style={{background:'#9b59b6', color:'white'}}><tr><th style={{padding:'8px'}}>Fecha</th><th>Tipo</th><th>Cliente</th><th>Total</th><th>Débito</th></tr></thead>
                                     <tbody>
                                         {cargaAnalisis.ventas.map((v, i) => (
                                             <tr key={i} style={{borderBottom:'1px solid #eee'}}>
                                                 <td style={{padding:'8px'}}>{v.fecha}</td><td>{v.tipo_dte === '03' ? 'CCF' : 'CF'}</td><td>{v.receptor_nombre || "Público"}</td><td style={{fontWeight:'bold'}}>${v.total.toFixed(2)}</td><td style={{color: '#c0392b'}}>${v.iva.toFixed(2)}</td>
                                             </tr>
                                         ))}
                                     </tbody>
                                 </table>
                             </div>
                         )}
                         <div style={{display:'flex', gap:'10px', justifyContent:'flex-end'}}>
                             <button onClick={() => setCargaAnalisis({compras:[], ventas:[], ignorados:[], retenciones:[], resumen:{total_iva_compras:0, total_iva_ventas:0}})} style={{padding:'15px', border:'none', background:'#95a5a6', color:'white', borderRadius:'5px', cursor:'pointer'}}>Limpiar</button>
                             <button onClick={() => { if(window.confirm("¿Guardar todo?")) { fetch('https://backend-production-8f98.up.railway.app/api/clientes/api/sistema/guardar-lote/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nrc_activo: clienteActivo, compras: cargaAnalisis.compras, ventas: cargaAnalisis.ventas, retenciones: cargaAnalisis.retenciones }) }).then(r => r.json()).then(res => { alert(`✅ Guardados: ${res.resumen.guardados} (Duplicados: ${res.resumen.duplicados})`); setCargaAnalisis({compras:[], ventas:[], ignorados:[], retenciones:[], resumen:{total_iva_compras:0, total_iva_ventas:0}}); setVistaActual("dashboard"); }); } }} style={{padding:'15px 30px', border:'none', background:'#27ae60', color:'white', borderRadius:'5px', cursor:'pointer', fontWeight:'bold', fontSize:'1.1em'}}>💾 GUARDAR TODO</button>
                         </div>
                     </div>
                 )}
              </div>
            )}

            {/* --- VISTA: NUEVA RETENCION --- */}
            {vistaActual === "nuevaRetencion" && (
              <div style={{ background: 'white', padding: '30px', borderRadius: '10px', maxWidth: '800px', margin: '0 auto' }}>
                 <div style={{display: 'flex', alignItems: 'center', marginBottom: '20px'}}>
                  <button onClick={() => setVistaActual("dashboard")} style={{marginRight: '15px', cursor: 'pointer', fontSize: '1.5em', border:'none', background:'transparent'}}>⬅️</button>
                  <h2 style={{margin: 0, color: '#27ae60'}}>💰 Registrar Retención MH</h2>
                </div>
                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '20px'}}>
                    <div>
                        <label style={{display:'block', fontWeight:'bold'}}>Tipo Anexo</label>
                        <select id="ret_tipo" value={retTipo} onChange={(e)=>setRetTipo(e.target.value)} style={{width:'100%', padding:'10px'}}>
                            <option value="162">Casilla 162 - IVA 1% (Anexo 7)</option>
                            <option value="161">Casilla 161 - Tarjeta (Anexo 6)</option>
                        </select>
                    </div>
                    <div><label style={{display:'block', fontWeight:'bold'}}>Fecha Doc</label><input type="date" value={retFecha} onChange={(e)=>setRetFecha(e.target.value)} style={{width:'100%', padding:'8px'}} /></div>
                </div>
                <div style={{background: '#f9f9f9', padding: '15px', borderRadius: '8px', marginBottom: '20px'}}>
                    <h4 style={{marginTop:0}}>Datos del Agente Retenedor</h4>
                    <div style={{display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '10px'}}>
                        <div><label style={{fontSize:'0.9em'}}>NIT Retenedor (Sin guiones)</label><input placeholder="0614..." value={retNit} onChange={(e)=>setRetNit(e.target.value)} style={{width:'100%', padding:'8px', border:'1px solid #ccc'}} /></div>
                        <div><label style={{fontSize:'0.9em'}}>Nombre Retenedor</label><input placeholder="Banco / Cliente" value={retEmisor} onChange={(e)=>setRetEmisor(e.target.value)} style={{width:'100%', padding:'8px', border:'1px solid #ccc'}} /></div>
                    </div>
                </div>
                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '20px'}}>
                    <div><label style={{fontSize:'0.9em'}}>Serie / Código DTE</label><input value={retCodigo} onChange={(e)=>setRetCodigo(e.target.value)} style={{width:'100%', padding:'8px'}} /></div>
                    <div><label style={{fontSize:'0.9em'}}>Número Documento</label><input placeholder="Correlativo" value={retNumero} onChange={(e)=>setRetNumero(e.target.value)} style={{width:'100%', padding:'8px'}} /></div>
                </div>
                <div style={{background: '#e8f8f5', padding: '15px', borderRadius: '8px', marginBottom: '20px', display:'grid', gridTemplateColumns:'1fr 1fr', gap:'15px'}}>
                    <div><label style={{display:'block', fontWeight:'bold'}}>Monto Sujeto ($)</label><input type="number" value={retMontoSujeto} onChange={(e)=>setRetMontoSujeto(e.target.value)} style={{width:'100%', padding:'10px'}} /></div>
                    <div><label style={{display:'block', fontWeight:'bold', color:'#27ae60'}}>Monto Retenido ($)</label><input type="number" value={retMonto} onChange={(e)=>setRetMonto(e.target.value)} style={{width:'100%', padding:'10px', border:'2px solid #27ae60'}} /></div>
                </div>
                <button onClick={guardarRetencionEnBackend} style={{marginTop: '20px', width: '100%', padding: '15px', background: '#27ae60', color: 'white', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer'}}>Guardar Retención</button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;