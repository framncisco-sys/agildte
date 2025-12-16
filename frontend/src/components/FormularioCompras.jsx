import React, { useState, useEffect } from 'react';
import { usePeriodo } from '../contexts/PeriodoContext';

const FormularioCompras = ({ clienteInfo, volverAlInicio, compraId = null }) => {
  // --- CONTEXTO GLOBAL ---
  const { periodoFormateado, mes, anio } = usePeriodo();
  
  // --- ESTADOS DEL FORMULARIO ---
  const [tipoDocumento, setTipoDocumento] = useState("03");
  const [fechaFactura, setFechaFactura] = useState("");
  const [numeroDocumento, setNumeroDocumento] = useState("");
  const [nrcProveedor, setNrcProveedor] = useState("");
  const [nombreProveedor, setNombreProveedor] = useState("");
  const [montoGravado, setMontoGravado] = useState("");
  const [montoIva, setMontoIva] = useState("");
  const [montoTotal, setMontoTotal] = useState("");
  const [modoEdicion, setModoEdicion] = useState(false);
  const [cargandoDatos, setCargandoDatos] = useState(false);
    
  // NUEVO: Estados para la búsqueda/creación de proveedor
  const [isLoadingProveedor, setIsLoadingProveedor] = useState(false);
  const [existeProveedor, setExisteProveedor] = useState(false);
  const [nombreBloqueado, setNombreBloqueado] = useState(false);
  const [modoCrearProveedor, setModoCrearProveedor] = useState(false);
  
  // Clasificaciones
  const [clasif1, setClasif1] = useState("");
  const [clasif2, setClasif2] = useState("");
  const [clasif3, setClasif3] = useState("");

  // Alertas
  const [alertaFecha, setAlertaFecha] = useState("");
  const [alertaVencimiento, setAlertaVencimiento] = useState("");

  // --- CARGAR DATOS SI HAY ID (MODO EDICIÓN) ---
  useEffect(() => {
    if (compraId) {
      setCargandoDatos(true);
      setModoEdicion(true);
      fetch(`http://127.0.0.1:8000/api/compras/${compraId}/`)
        .then(res => res.json())
        .then(data => {
          // Mapear datos del backend a los estados del formulario
          setTipoDocumento(data.tipo_documento || "03");
          setFechaFactura(data.fecha_emision || "");
          setNumeroDocumento(data.codigo_generacion || "");
          setNrcProveedor(data.nrc_proveedor || "");
          setNombreProveedor(data.nombre_proveedor || "");
          setMontoGravado(data.monto_gravado?.toString() || "");
          setMontoIva(data.monto_iva?.toString() || "");
          setMontoTotal(data.monto_total?.toString() || "");
          setClasif1(data.clasificacion_1 || "");
          setClasif2(data.clasificacion_2 || "");
          setClasif3(data.clasificacion_3 || "");
          // Si el proveedor existe, marcar como existente
          if (data.nrc_proveedor) {
            setExisteProveedor(true);
            setNombreBloqueado(true);
          }
          setCargandoDatos(false);
        })
        .catch(error => {
          console.error("Error cargando compra:", error);
          alert("Error al cargar los datos de la compra");
          setCargandoDatos(false);
        });
    }
  }, [compraId]);

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

  // --- VALIDACIÓN DE FECHA Y REGLA DE 3 MESES (Solo en onBlur) ---
  const handleFechaBlur = (e) => {
    const fecha = e.target.value;
    
    if (!fecha) {
      setAlertaFecha("");
      setAlertaVencimiento("");
      return;
    }
    
    const fechaDoc = new Date(fecha);
    const hoy = new Date();
    
    // Validación 1: Fecha futura
    if (fechaDoc > hoy) {
      setAlertaFecha("⚠️ Cuidado: Estás registrando una fecha futura.");
      setAlertaVencimiento("");
      return;
    }
    
    setAlertaFecha("");
    
    // Validación 2: REGLA DE LOS 3 MESES (Solo para CCF - tipo 03)
    if (tipoDocumento === "03") {
      // Calcular la fecha de referencia (final del periodo actual)
      const fechaPeriodo = new Date(anio, mes, 0); // Último día del mes del periodo
      
      // Calcular diferencia en días
      const diferenciaMs = fechaPeriodo.getTime() - fechaDoc.getTime();
      const diferenciaDias = Math.floor(diferenciaMs / (1000 * 60 * 60 * 24));
      
      // Si tiene más de 90 días (3 meses), el IVA ya no es deducible
      if (diferenciaDias > 90) {
        const mesesVencidos = Math.floor(diferenciaDias / 30);
        
        // Cambiar automáticamente a "14 - Sujeto Excluido" (Gasto no deducible)
        setTipoDocumento("14");
        setAlertaVencimiento(
          `⚠️ Atención: Este documento tiene más de ${mesesVencidos} meses (${diferenciaDias} días). El IVA ya no es deducible. Se cambiará automáticamente a "Sujeto Excluido" (Gasto - No Deducible).`
        );
        
        // Mostrar alerta al usuario
        alert(
          `⚠️ ATENCIÓN: Este documento tiene más de 3 meses (${diferenciaDias} días).\n\n` +
          `Por ley, el IVA ya no es deducible después de 3 meses.\n\n` +
          `El sistema cambiará automáticamente el tipo de documento a "14 - Sujeto Excluido" (Gasto - No Deducible).`
        );
      } else {
        setAlertaVencimiento("");
      }
    } else {
      setAlertaVencimiento("");
    }
  };

  // --- BUSCAR PROVEEDOR (Al escribir NRC - onBlur) ---
  const buscarProveedor = async () => {
    if(nrcProveedor.length < 5) {
      // Resetear estados si el NRC es muy corto
      setExisteProveedor(false);
      setNombreBloqueado(false);
      setModoCrearProveedor(false);
      setNombreProveedor("");
      return;
    }
    
    setIsLoadingProveedor(true);
    
    try {
        // Buscar proveedor por NRC usando filtro del backend
        const res = await fetch(`http://127.0.0.1:8000/api/clientes/?nrc=${nrcProveedor}`);
        
        if(res.ok) {
            const data = await res.json();
            const proveedorEncontrado = Array.isArray(data) && data.length > 0 ? data[0] : null;
            
            if(proveedorEncontrado) {
                // ESCENARIO A: El proveedor EXISTE
                setNombreProveedor(proveedorEncontrado.nombre);
                setExisteProveedor(true);
                setNombreBloqueado(true); // Bloquear campo nombre
                setModoCrearProveedor(false);
            } else {
                // ESCENARIO B: El proveedor NO EXISTE
                setExisteProveedor(false);
                setNombreBloqueado(false);
                setNombreProveedor(""); // Limpiar nombre
                
                // Preguntar si desea crearlo
                const deseaCrear = window.confirm(
                    `⚠️ Este proveedor (NRC: ${nrcProveedor}) no existe en la base de datos.\n\n¿Deseas crearlo ahora?`
                );
                
                if(deseaCrear) {
                    setModoCrearProveedor(true);
                    setNombreBloqueado(false); // Desbloquear para que escriba el nombre
                } else {
                    setModoCrearProveedor(false);
                }
            }
        }
    } catch (error) {
        console.error("Error buscando proveedor:", error);
        alert("Error al buscar proveedor. Verifica tu conexión.");
    } finally {
        setIsLoadingProveedor(false);
    }
  };

  // --- CREAR PROVEEDOR (Cuando el usuario escribe el nombre y sale del campo) ---
  const crearProveedor = async () => {
    if(!nombreProveedor || nombreProveedor.trim() === "") {
      alert("⚠️ Debes escribir el nombre del proveedor antes de guardarlo.");
      return;
    }

    if(!nrcProveedor || nrcProveedor.length < 5) {
      alert("⚠️ El NRC del proveedor es inválido.");
      return;
    }

    const confirmarCrear = window.confirm(
      `¿Deseas guardar el proveedor "${nombreProveedor}" (NRC: ${nrcProveedor}) ahora?`
    );

    if(!confirmarCrear) return;

    setIsLoadingProveedor(true);

    try {
      const nuevoProveedor = {
        nrc: nrcProveedor,
        nombre: nombreProveedor,
        nit: "", // Opcional
      };

      const res = await fetch('http://127.0.0.1:8000/api/clientes/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nuevoProveedor)
      });

      if(res.ok) {
        alert("✅ Proveedor creado exitosamente");
        setExisteProveedor(true);
        setNombreBloqueado(true); // Bloquear después de crear
        setModoCrearProveedor(false);
      } else {
        const errorData = await res.json();
        alert(`❌ Error al crear proveedor: ${JSON.stringify(errorData)}`);
      }
    } catch (error) {
      console.error("Error creando proveedor:", error);
      alert("Error de conexión al crear proveedor.");
    } finally {
      setIsLoadingProveedor(false);
    }
  };

  // --- GUARDAR COMPRA ---
const guardarCompra = async (terminar) => {
    // 1. Validar que el usuario escribió algo
    if (!montoGravado || !nrcProveedor || !nombreProveedor) {
        alert("⚠️ Faltan datos: Revisa el Monto, NRC Proveedor o Nombre Proveedor");
        return;
    }

    // Validar que el proveedor existe antes de guardar
    if (!existeProveedor && !modoCrearProveedor) {
        alert("⚠️ Debes buscar y crear el proveedor antes de guardar la compra.");
        return;
    }

    // 2. Preparar el paquete de datos según el modelo Compra
    const nuevaCompra = {
        empresa: clienteInfo.id || null,     // ID de la empresa (opcional)
        proveedor: nrcProveedor,             // NRC del proveedor (clave foránea)
        nrc_proveedor: nrcProveedor,         // Requerido por backend
        nombre_proveedor: nombreProveedor,    // Requerido por backend
        fecha_emision: fechaFactura,
        periodo_aplicado: periodoFormateado,  // Usar período del contexto global
        codigo_generacion: numeroDocumento || null, // Código del documento
        monto_gravado: parseFloat(montoGravado) || 0,
        monto_iva: parseFloat(montoIva) || 0,
        monto_total: parseFloat(montoTotal) || 0,
        tipo_documento: tipoDocumento,        // "03", "05", "12", "14"
        
        // Opcionales
        clasificacion_1: clasif1 || "Gravada",
        clasificacion_2: clasif2 || "",
        clasificacion_3: clasif3 || "",
        estado: "Registrado"
    };

    console.log("📤 ENVIANDO COMPRA (Revisar en Consola):", nuevaCompra);

    try {
        const url = modoEdicion 
            ? `http://127.0.0.1:8000/api/compras/actualizar/${compraId}/`
            : 'http://127.0.0.1:8000/api/compras/crear/';
        
        const metodo = modoEdicion ? 'PUT' : 'POST';

        const respuesta = await fetch(url, {
            method: metodo,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(nuevaCompra)
        });

        if (respuesta.ok) {
            alert(modoEdicion ? "✅ Compra Actualizada con Éxito" : "✅ Compra Guardada con Éxito");
            // Limpiar todo
            setMontoGravado(""); setMontoIva(""); setMontoTotal("");
            setNumeroDocumento(""); setNrcProveedor(""); setNombreProveedor("");
            setExisteProveedor(false);
            setNombreBloqueado(false);
            setModoCrearProveedor(false);
            setModoEdicion(false);
            if (terminar) volverAlInicio();
        } else {
            // Si falla, mostramos el error técnico en una alerta para que lo veas
            const errorData = await respuesta.json();
            console.error("❌ Error del servidor:", errorData);
            alert(`Error al guardar: ${JSON.stringify(errorData)}`);
        }
    } catch (error) {
        console.error("Error de red:", error);
        alert("Error de conexión con el servidor");
    }
  };

  return (
    <div style={{ background: 'white', padding: '30px', borderRadius: '10px', maxWidth: '900px', margin: '20px auto', boxShadow: '0 4px 10px rgba(0,0,0,0.1)' }}>
        
        {/* ENCABEZADO */}
        <div style={{display: 'flex', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #eee', paddingBottom: '10px'}}>
            <button onClick={volverAlInicio} style={{marginRight: '15px', cursor: 'pointer', border: 'none', background: 'transparent', fontSize: '1.5em'}}>⬅️</button>
            <h2 style={{margin: 0, color: '#3498db'}}>
                {modoEdicion ? '✏️ Editar Compra' : '📝 Registrar Nueva Compra'}
            </h2>
            <span style={{marginLeft: 'auto', fontSize: '0.9em', color: '#7f8c8d'}}>{clienteInfo.nombre}</span>
        </div>
        
        {cargandoDatos && (
            <div style={{padding: '20px', textAlign: 'center', background: '#f0f0f0', borderRadius: '5px', marginBottom: '20px'}}>
                ⏳ Cargando datos de la compra...
            </div>
        )}
        
        {/* INFO PERÍODO (Desde barra superior) */}
        <div style={{marginBottom: '20px', padding: '10px', background: '#e8f6f3', borderRadius: '5px', fontSize: '0.9em', color: '#27ae60'}}>
            📅 Período aplicado: <strong>{periodoFormateado}</strong> (configurado en la barra superior)
        </div>

        {/* FILA 1 */}
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px', marginBottom: '20px'}}>
            <div>
                <label style={{display: 'block'}}>Tipo Doc</label>
                <select 
                    value={tipoDocumento} 
                    onChange={(e) => {
                        setTipoDocumento(e.target.value);
                        // Si cambia el tipo de documento, limpiar alerta de vencimiento
                        setAlertaVencimiento("");
                        // Si hay fecha y es tipo 03, re-validar al cambiar tipo
                        if (fechaFactura && e.target.value === "03") {
                            // Simular blur para re-validar
                            const event = { target: { value: fechaFactura } };
                            handleFechaBlur(event);
                        }
                    }} 
                    style={{width: '100%', padding: '10px'}}
                >
                    <option value="03">03 - CCF (Crédito Fiscal - Deducible)</option>
                    <option value="05">05 - Nota Crédito</option>
                    <option value="14">14 - Sujeto Excluido (Gasto - No Deducible)</option>
                    {clienteInfo?.es_importador && <option value="12">12 - Importación</option>}
                </select>
            </div>
            <div>
                <label style={{display: 'block'}}>Fecha</label>
                <input 
                    type="date" 
                    value={fechaFactura} 
                    onChange={(e) => {
                        // Solo actualizar el estado, sin validar
                        setFechaFactura(e.target.value);
                        // Limpiar alertas mientras escribe
                        setAlertaFecha("");
                        setAlertaVencimiento("");
                    }}
                    onBlur={handleFechaBlur}
                    style={{
                        width: '100%', 
                        padding: '8px', 
                        border: (alertaFecha || alertaVencimiento) ? '2px solid #e74c3c' : '1px solid #ccc'
                    }}
                />
                {alertaFecha && <small style={{color:'#e74c3c', display:'block', marginTop: '5px'}}>{alertaFecha}</small>}
                {alertaVencimiento && (
                    <div style={{
                        marginTop: '10px', 
                        padding: '10px', 
                        background: '#fff3cd', 
                        border: '1px solid #ffc107', 
                        borderRadius: '5px',
                        fontSize: '0.9em'
                    }}>
                        <strong>⚠️ {alertaVencimiento}</strong>
                    </div>
                )}
            </div>
            <div>
                <label style={{display: 'block'}}>Nº Doc</label>
                <input value={numeroDocumento} onChange={(e) => setNumeroDocumento(e.target.value)} style={{width: '100%', padding: '10px', border: '1px solid #ccc'}} />
            </div>
        </div>

        {/* FILA 2: PROVEEDOR */}
        <div style={{display: 'flex', gap: '10px', marginBottom: '20px', alignItems: 'center'}}>
            <div style={{width: '30%', position: 'relative'}}>
                <input 
                    placeholder="NRC Proveedor" 
                    value={nrcProveedor} 
                    onChange={(e) => {
                        setNrcProveedor(e.target.value);
                        // Resetear estados cuando cambia el NRC
                        setExisteProveedor(false);
                        setNombreBloqueado(false);
                        setModoCrearProveedor(false);
                        setNombreProveedor("");
                    }} 
                    onBlur={buscarProveedor} 
                    style={{padding:'10px', width: '100%'}}
                    disabled={isLoadingProveedor}
                />
                {isLoadingProveedor && (
                    <span style={{position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.8em', color: '#7f8c8d'}}>
                        🔍 Buscando...
                    </span>
                )}
            </div>
            <div style={{flex: 1, position: 'relative'}}>
                <input 
                    placeholder={modoCrearProveedor ? "Escribe el nombre del proveedor" : "Nombre Proveedor"} 
                    value={nombreProveedor} 
                    onChange={(e)=>setNombreProveedor(e.target.value)} 
                    onBlur={modoCrearProveedor ? crearProveedor : undefined}
                    readOnly={nombreBloqueado}
                    style={{
                        padding:'10px', 
                        width: '100%',
                        background: nombreBloqueado ? '#e9ecef' : 'white',
                        cursor: nombreBloqueado ? 'not-allowed' : 'text',
                        border: existeProveedor ? '2px solid #27ae60' : '1px solid #ccc'
                    }} 
                />
                {existeProveedor && (
                    <span style={{position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.8em', color: '#27ae60'}}>
                        ✅ Existe
                    </span>
                )}
                {modoCrearProveedor && !existeProveedor && (
                    <span style={{position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.8em', color: '#f39c12'}}>
                        ✏️ Nuevo
                    </span>
                )}
            </div>
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