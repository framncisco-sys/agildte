import React, { useState, useEffect } from 'react';

const FormularioCompras = ({ clienteInfo, volverAlInicio }) => {
  // --- ESTADOS DEL FORMULARIO ---
  const [tipoDocumento, setTipoDocumento] = useState("03");
  const [fechaFactura, setFechaFactura] = useState("");
  const [numeroDocumento, setNumeroDocumento] = useState("");
  const [nrcProveedor, setNrcProveedor] = useState("");
  const [nombreProveedor, setNombreProveedor] = useState("");
  const [montoGravado, setMontoGravado] = useState("");
  const [montoIva, setMontoIva] = useState("");
  const [montoTotal, setMontoTotal] = useState("");
    
  // NUEVO: Estado para el Periodo (Mes de trabajo)
  const [periodoContable, setPeriodoContable] = useState(""); 
  const [listaPeriodos, setListaPeriodos] = useState([]);

  // NUEVO: Al cargar el formulario, calculamos: Mes Actual y Mes Siguiente
  useEffect(() => {
    const hoy = new Date();
    
    // Mes Actual
    const mesActual = hoy.toISOString().slice(0, 7); // Ejemplo: "2025-12"
    
    // Mes Siguiente (Manejo automático de cambio de año)
    const proximoMesDate = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 1);
    const mesSiguiente = proximoMesDate.toISOString().slice(0, 7); // Ejemplo: "2026-01"

    setListaPeriodos([mesActual, mesSiguiente]);
    setPeriodoContable(mesActual); // Por defecto selecciona el actual
  }, []);
  
  // Clasificaciones
  const [clasif1, setClasif1] = useState("");
  const [clasif2, setClasif2] = useState("");
  const [clasif3, setClasif3] = useState("");

  // Alertas
  const [alertaFecha, setAlertaFecha] = useState("");

  // --- DATOS FIJOS (LISTAS) ---
  const opcionesGasto = {
    "Gastos de Venta": ["Sueldos y Comisiones", "Publicidad", "Transporte"],
    "Gastos de Administración": ["Sueldos Oficina", "Papelería", "Servicios Básicos (Luz/Agua)", "Alquileres"],
    "Gastos Financieros": ["Intereses Bancarios", "Comisiones Tarjetas"],
    "Costo de Venta": ["Compras de Mercadería", "Fletes sobre Compras"]
  };

  const opcionesSector = {
    "Servicios Básicos (Luz/Agua)": ["Energía Eléctrica", "Agua Potable", "Telecomunicaciones"],
    "Compras de Mercadería": ["Local", "Importación"],
    // Puedes agregar más sub-clasificaciones aquí si las necesitas
  };

  // --- CALCULOS AUTOMATICOS ---
  const handleMontoChange = (e) => {
    const gravado = parseFloat(e.target.value) || 0;
    setMontoGravado(gravado);
    
    // Calcular IVA (13%)
    const iva = parseFloat((gravado * 0.13).toFixed(2));
    setMontoIva(iva);
    
    // Total
    setMontoTotal((gravado + iva).toFixed(2));
  };

  // --- VALIDACIÓN DE FECHA (Periodo Actual) ---
  const validarFecha = (fecha) => {
    setFechaFactura(fecha);
    const fechaObj = new Date(fecha);
    const hoy = new Date();
    
    // Ejemplo de validación simple: Avisar si la fecha es de un mes futuro
    if (fechaObj.getMonth() > hoy.getMonth() && fechaObj.getFullYear() === hoy.getFullYear()) {
      setAlertaFecha("⚠️ Cuidado: Estás registrando una fecha futura.");
    } else {
      setAlertaFecha("");
    }
  };

  // --- BUSCAR PROVEEDOR (Al escribir NRC) ---
  const buscarProveedor = async () => {
    if(nrcProveedor.length < 5) return; // No buscar si es muy corto
    
    try {
        // Asumiendo que tienes un endpoint para buscar proveedores. 
        // Si no existe, este fetch fallará silenciosamente sin romper nada.
        const res = await fetch(`https://backend-production-8f98.up.railway.app/api/proveedores/buscar/?nrc=${nrcProveedor}`);
        if(res.ok) {
            const data = await res.json();
            if(data.nombre) setNombreProveedor(data.nombre);
        }
    } catch (error) {
        console.log("No se encontró proveedor automático, ingresarlo manual.");
    }
  };

  // --- GUARDAR COMPRA ---
  const guardarCompra = async (terminar) => {
    if (!montoGravado || !nrcProveedor || !fechaFactura) {
        alert("Faltan datos obligatorios (Monto, NRC o Fecha)");
        return;
    }

    const nuevaCompra = {
        empresa_nrc: clienteInfo.nrc, // Vinculamos la compra a la empresa seleccionada
        fecha: fechaFactura,
        numero_documento: numeroDocumento,
        nrc_proveedor: nrcProveedor,
        nombre_proveedor: nombreProveedor,
        total_gravado: parseFloat(montoGravado),
        total_iva: parseFloat(montoIva),
        total: parseFloat(montoTotal),
        tipo_documento: tipoDocumento,
        clasificacion_1: clasif1,
        clasificacion_2: clasif2,
        clasificacion_3: clasif3
    };
    // --- AGREGA ESTA LÍNEA AQUÍ: ---
    console.log("📤 ENVIANDO COMPRA:", nuevaCompra); 
    // -------------------------------

    try {
        const respuesta = await fetch('https://backend-production-8f98.up.railway.app/api/compras/crear/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(nuevaCompra)
        });

        if (respuesta.ok) {
            alert("✅ Compra Guardada");
            // Limpiar formulario
            setMontoGravado(""); setMontoIva(""); setMontoTotal("");
            setNumeroDocumento(""); setNrcProveedor(""); setNombreProveedor("");
            
            if (terminar) {
                volverAlInicio();
            }
        } else {
            alert("❌ Error al guardar (Revisa la consola)");
        }
    } catch (error) {
        console.error(error);
        alert("Error de conexión");
    }
  };

  return (
    <div style={{ background: 'white', padding: '30px', borderRadius: '10px', maxWidth: '900px', margin: '20px auto', boxShadow: '0 4px 10px rgba(0,0,0,0.1)' }}>
        
        {/* ENCABEZADO */}
        <div style={{display: 'flex', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #eee', paddingBottom: '10px'}}>
            <button onClick={volverAlInicio} style={{marginRight: '15px', cursor: 'pointer', border: 'none', background: 'transparent', fontSize: '1.5em'}}>⬅️</button>
            <h2 style={{margin: 0, color: '#3498db'}}>📝 Registrar Nueva Compra</h2>
            <span style={{marginLeft: 'auto', fontSize: '0.9em', color: '#7f8c8d'}}>{clienteInfo.nombre}</span>
        </div>

        {/* FILA 1 */}
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px', marginBottom: '20px'}}>
            <div>
                <label style={{display: 'block'}}>Tipo Doc</label>
                <select value={tipoDocumento} onChange={(e) => setTipoDocumento(e.target.value)} style={{width: '100%', padding: '10px'}}>
                    <option value="03">03 - CCF</option>
                    <option value="05">05 - Nota Crédito</option>
                    <option value="14">14 - Sujeto Excluido</option>
                    {clienteInfo?.es_importador && <option value="12">12 - Importación</option>}
                </select>
            </div>
            <div>
                <label style={{display: 'block'}}>Fecha</label>
                <input type="date" value={fechaFactura} onChange={(e) => validarFecha(e.target.value)} style={{width: '100%', padding: '8px', border: alertaFecha ? '2px solid red' : '1px solid #ccc'}} />
                {alertaFecha && <small style={{color:'red', display:'block'}}>{alertaFecha}</small>}
            </div>
            <div>
                <label style={{display: 'block'}}>Nº Doc</label>
                <input value={numeroDocumento} onChange={(e) => setNumeroDocumento(e.target.value)} style={{width: '100%', padding: '10px', border: '1px solid #ccc'}} />
            </div>
        </div>

        {/* FILA 2: PROVEEDOR */}
        <div style={{display: 'flex', gap: '10px', marginBottom: '20px'}}>
            <input placeholder="NRC Proveedor" value={nrcProveedor} onChange={(e) => setNrcProveedor(e.target.value)} onBlur={buscarProveedor} style={{padding:'10px', width:'30%'}} />
            <input placeholder="Nombre Proveedor" value={nombreProveedor} onChange={(e)=>setNombreProveedor(e.target.value)} style={{padding:'10px', flex: 1}} />
        </div>

        {/* FILA 3: MONTOS */}
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '20px', background: '#f8f9fa', padding: '15px', borderRadius: '5px'}}>
            <div>
                <label>Gravado</label>
                <input type="number" placeholder="0.00" value={montoGravado} onChange={handleMontoChange} style={{padding:'10px', width: '100%'}} />
            </div>
            <div>
                <label>IVA (13%)</label>
                <input type="number" value={montoIva} readOnly style={{padding:'10px', width: '100%', background:'#e9ecef'}} />
            </div>
            <div>
                <label>Total</label>
                <input type="number" value={montoTotal} readOnly style={{padding:'10px', width: '100%', background:'#e9ecef', fontWeight: 'bold'}} />
            </div>
        </div>

        {/* FILA 4: CLASIFICACION GASTOS */}
        <div style={{display: 'flex', gap: '10px', marginBottom: '20px'}}>
             <select value={clasif1} onChange={(e) => {setClasif1(e.target.value); setClasif2("");}} style={{flex:1, padding:'10px'}}>
                <option value="">-- Clasificación 1 --</option>
                {Object.keys(opcionesGasto).map(op=><option key={op}>{op}</option>)}
             </select>

             <select value={clasif2} onChange={(e) => {setClasif2(e.target.value); setClasif3("");}} disabled={!clasif1} style={{flex:1, padding:'10px'}}>
                <option value="">-- Clasificación 2 --</option>
                {clasif1 && opcionesGasto[clasif1]?.map(op=><option key={op}>{op}</option>)}
             </select>
        </div>

        {/* BOTONES */}
        <div style={{marginTop: '30px', display: 'flex', justifyContent: 'flex-end', gap: '10px'}}>
            <button onClick={() => guardarCompra(false)} style={{padding: '15px 20px', background: '#34495e', color: 'white', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer'}}>
                ➕ Guardar y Otra
            </button>
            <button onClick={() => guardarCompra(true)} style={{padding: '15px 30px', background: '#27ae60', color: 'white', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer'}}>
                💾 Guardar y Terminar
            </button>
        </div>
    </div>
  );
};

export default FormularioCompras;