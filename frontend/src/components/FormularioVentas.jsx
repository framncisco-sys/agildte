import React, { useState, useEffect } from 'react';
import { usePeriodo } from '../contexts/PeriodoContext';

const FormularioVentas = ({ clienteInfo, volverAlInicio, ventaId = null }) => {
  // --- CONTEXTO GLOBAL ---
  const { periodoFormateado, mes, anio } = usePeriodo();
  
  // --- ESTADOS ---
  const [tipoDocumento, setTipoDocumento] = useState("CCF"); 
  const [fechaFactura, setFechaFactura] = useState("");
  const [numeroDocumento, setNumeroDocumento] = useState("");
  
  // Datos del Cliente (El que compra en la ferretería)
  const [nrcCliente, setNrcCliente] = useState("");
  const [nombreCliente, setNombreCliente] = useState("");
  
  // NUEVO: Estados para la búsqueda/creación de cliente
  const [isLoadingCliente, setIsLoadingCliente] = useState(false);
  const [existeCliente, setExisteCliente] = useState(false);
  const [nombreBloqueado, setNombreBloqueado] = useState(false);
  const [modoCrearCliente, setModoCrearCliente] = useState(false);
  const [modoEdicion, setModoEdicion] = useState(false);
  const [cargandoDatos, setCargandoDatos] = useState(false);

  // Montos
  const [montoGravado, setMontoGravado] = useState("");
  const [montoIva, setMontoIva] = useState("");
  const [montoTotal, setMontoTotal] = useState("");

  // --- USE EFFECT: Cargar Fecha Automática ---
  useEffect(() => {
    if (!ventaId) {
      const hoy = new Date();
      setFechaFactura(hoy.toISOString().slice(0, 10));
    }
  }, []);

  // --- CARGAR DATOS SI HAY ID (MODO EDICIÓN) ---
  useEffect(() => {
    if (ventaId) {
      setCargandoDatos(true);
      setModoEdicion(true);
      fetch(`http://127.0.0.1:8000/api/ventas/${ventaId}/`)
        .then(res => res.json())
        .then(data => {
          // Mapear datos del backend a los estados del formulario
          setTipoDocumento(data.tipo_venta || "CCF");
          setFechaFactura(data.fecha_emision || "");
          setNumeroDocumento(data.numero_documento || data.codigo_generacion || "");
          setMontoGravado(data.venta_gravada?.toString() || "");
          setMontoIva(data.debito_fiscal?.toString() || "");
          setMontoTotal((parseFloat(data.venta_gravada || 0) + parseFloat(data.debito_fiscal || 0)).toString());
          
          // Si no es CF, cargar datos del cliente
          if (data.tipo_venta !== 'CF') {
            // El serializer ahora envía nrc_receptor y nombre_receptor directamente
            const nrcCliente = data.nrc_receptor || (typeof data.cliente === 'string' ? data.cliente : data.cliente?.nrc) || "";
            const nombreCliente = data.nombre_receptor || (typeof data.cliente === 'object' && data.cliente ? data.cliente.nombre : "") || "";
            
            if (nrcCliente) {
              setNrcCliente(nrcCliente);
              setNombreCliente(nombreCliente);
              setExisteCliente(true);
              setNombreBloqueado(true);
            }
          }
          setCargandoDatos(false);
        })
        .catch(error => {
          console.error("Error cargando venta:", error);
          alert("Error al cargar los datos de la venta");
          setCargandoDatos(false);
        });
    }
  }, [ventaId]);
  
  // Determinar si es Consumidor Final
  const esConsumidorFinal = tipoDocumento === "CF";

  // --- CALCULOS ---
  const handleMontoChange = (e, tipoCampo = 'base') => {
    const valorIngresado = parseFloat(e.target.value) || 0;
    
    if (esConsumidorFinal) {
      // LÓGICA CF: IVA INCLUIDO
      // El usuario escribe el TOTAL (con IVA incluido) en el primer campo
      // Calculamos hacia atrás:
      const total = valorIngresado;
      const subtotal = parseFloat((total / 1.13).toFixed(2)); // Base sin IVA
      const iva = parseFloat((total - subtotal).toFixed(2)); // IVA = Total - Subtotal
      
      setMontoGravado(subtotal); // Guardamos la base (sin IVA) para el backend
      setMontoIva(iva);
      setMontoTotal(total.toFixed(2));
    } else {
      // LÓGICA CCF: IVA AGREGADO
      // El usuario escribe la BASE (sin IVA) en el primer campo
      // Calculamos hacia adelante:
      const gravado = valorIngresado;
      const iva = parseFloat((gravado * 0.13).toFixed(2));
      const total = gravado + iva;
      
      setMontoGravado(gravado);
      setMontoIva(iva);
      setMontoTotal(total.toFixed(2));
    }
  };

  // --- BUSCAR CLIENTE (Al escribir NRC - onBlur) ---
  const buscarCliente = async () => {
    if(nrcCliente.length < 5) {
      // Resetear estados si el NRC es muy corto
      setExisteCliente(false);
      setNombreBloqueado(false);
      setModoCrearCliente(false);
      setNombreCliente("");
      return;
    }
    
    setIsLoadingCliente(true);
    
    try {
        // Buscar cliente por NRC usando filtro del backend
        const res = await fetch(`http://127.0.0.1:8000/api/clientes/?nrc=${nrcCliente}`);
        
        if(res.ok) {
            const data = await res.json();
            const clienteEncontrado = Array.isArray(data) && data.length > 0 ? data[0] : null;
            
            if(clienteEncontrado) {
                // ESCENARIO A: El cliente EXISTE
                setNombreCliente(clienteEncontrado.nombre);
                setExisteCliente(true);
                setNombreBloqueado(true); // Bloquear campo nombre
                setModoCrearCliente(false);
            } else {
                // ESCENARIO B: El cliente NO EXISTE
                setExisteCliente(false);
                setNombreBloqueado(false);
                setNombreCliente(""); // Limpiar nombre
                
                // Preguntar si desea crearlo
                const deseaCrear = window.confirm(
                    `⚠️ Este cliente (NRC: ${nrcCliente}) no existe en la base de datos.\n\n¿Deseas crearlo ahora?`
                );
                
                if(deseaCrear) {
                    setModoCrearCliente(true);
                    setNombreBloqueado(false); // Desbloquear para que escriba el nombre
                } else {
                    setModoCrearCliente(false);
                }
            }
        }
    } catch (error) {
        console.error("Error buscando cliente:", error);
        alert("Error al buscar cliente. Verifica tu conexión.");
    } finally {
        setIsLoadingCliente(false);
    }
  };

  // --- CREAR CLIENTE (Cuando el usuario escribe el nombre y sale del campo) ---
  const crearCliente = async () => {
    if(!nombreCliente || nombreCliente.trim() === "") {
      alert("⚠️ Debes escribir el nombre del cliente antes de guardarlo.");
      return;
    }

    if(!nrcCliente || nrcCliente.length < 5) {
      alert("⚠️ El NRC del cliente es inválido.");
      return;
    }

    const confirmarCrear = window.confirm(
      `¿Deseas guardar el cliente "${nombreCliente}" (NRC: ${nrcCliente}) ahora?`
    );

    if(!confirmarCrear) return;

    setIsLoadingCliente(true);

    try {
      const nuevoCliente = {
        nrc: nrcCliente,
        nombre: nombreCliente,
        nit: "", // Opcional
      };

      const res = await fetch('http://127.0.0.1:8000/api/clientes/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nuevoCliente)
      });

      if(res.ok) {
        alert("✅ Cliente creado exitosamente");
        setExisteCliente(true);
        setNombreBloqueado(true); // Bloquear después de crear
        setModoCrearCliente(false);
      } else {
        const errorData = await res.json();
        alert(`❌ Error al crear cliente: ${JSON.stringify(errorData)}`);
      }
    } catch (error) {
      console.error("Error creando cliente:", error);
      alert("Error de conexión al crear cliente.");
    } finally {
      setIsLoadingCliente(false);
    }
  };

  // Estado para mostrar error de fecha
  const [errorFecha, setErrorFecha] = useState("");

  // --- VALIDAR FECHA CONTRA PERIODO (Solo para mostrar mensaje) ---
  const validarFechaContraPeriodo = (fecha) => {
    if (!fecha) return { valida: false, mensaje: "Debes seleccionar una fecha" };
    
    const fechaDoc = new Date(fecha);
    const mesDoc = fechaDoc.getMonth() + 1; // 1-12
    const anioDoc = fechaDoc.getFullYear();
    
    // Comparar con el periodo actual del contexto
    if (mesDoc !== mes || anioDoc !== anio) {
      const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
      const mesDocNombre = meses[mesDoc - 1];
      const mesActualNombre = meses[mes - 1];
      
      return {
        valida: false,
        mensaje: `Error: El documento es de ${mesDocNombre}-${anioDoc} pero estás trabajando en el periodo ${mesActualNombre}-${anio}. Cambia la fecha o el periodo de trabajo.`
      };
    }
    
    return { valida: true };
  };

  // --- HANDLE FECHA BLUR: Validar cuando el usuario sale del campo ---
  const handleFechaBlur = (e) => {
    const fecha = e.target.value;
    if (!fecha) {
      setErrorFecha("");
      return;
    }
    
    const validacion = validarFechaContraPeriodo(fecha);
    if (!validacion.valida) {
      setErrorFecha(validacion.mensaje);
      alert(`⚠️ ${validacion.mensaje}`);
    } else {
      setErrorFecha("");
    }
  };

  // --- GUARDAR VENTA ---
  const guardarVenta = async (terminar) => {
    if (!montoGravado || !fechaFactura) {
        alert("⚠️ Faltan datos obligatorios (Monto o Fecha)");
        return;
    }

    // VALIDACIÓN ESTRICTA: La fecha debe pertenecer al periodo actual
    const validacionFecha = validarFechaContraPeriodo(fechaFactura);
    if (!validacionFecha.valida) {
        alert(`❌ ${validacionFecha.mensaje}`);
        return;
    }

    // Validar cliente solo si NO es Consumidor Final
    if (!esConsumidorFinal) {
        if (!nrcCliente) {
            alert("⚠️ Debes proporcionar el NRC del cliente para ventas a Contribuyentes.");
            return;
        }
        if (!existeCliente && !modoCrearCliente) {
            alert("⚠️ Debes buscar y crear el cliente antes de guardar la venta.");
            return;
        }
    }

    const payloadVenta = {
        empresa: clienteInfo.id || null,     // ID de la empresa (opcional)
        // Para CF: no enviar cliente (o null explícito) - el backend lo maneja
        // Para CCF: enviar el NRC del cliente
        ...(esConsumidorFinal ? {} : { cliente: nrcCliente }),
        fecha_emision: fechaFactura,
        periodo_aplicado: periodoFormateado,  // Usar período del contexto global
        numero_documento: numeroDocumento || null,
        venta_gravada: parseFloat(montoGravado) || 0,  // Base sin IVA (ya calculada correctamente)
        debito_fiscal: parseFloat(montoIva) || 0,       // IVA calculado
        tipo_venta: tipoDocumento === "CCF" ? "CCF" : "CF", // Asegurar valores válidos
        nombre_receptor: esConsumidorFinal ? "Consumidor Final" : (nombreCliente || null),
        nrc_receptor: esConsumidorFinal ? "0000-000000-000-0" : (nrcCliente || null),
        clase_documento: "1",                // Default: Impreso por Imprenta
        clasificacion_venta: "1",           // Default: Gravada
        tipo_ingreso: "3"                    // Default: Comercial
    };

    try {
        const url = modoEdicion 
            ? `http://127.0.0.1:8000/api/ventas/actualizar/${ventaId}/`
            : 'http://127.0.0.1:8000/api/ventas/crear/';
        
        const metodo = modoEdicion ? 'PUT' : 'POST';

        const respuesta = await fetch(url, {
            method: metodo,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payloadVenta)
        });

        if (respuesta.ok) {
            alert(modoEdicion ? "✅ Venta Actualizada Exitosamente" : "✅ Venta Guardada Exitosamente");
            setMontoGravado(""); setMontoIva(""); setMontoTotal("");
            setNumeroDocumento(""); setNrcCliente(""); setNombreCliente("");
            setExisteCliente(false);
            setNombreBloqueado(false);
            setModoCrearCliente(false);
            setModoEdicion(false);
            if (terminar) volverAlInicio();
        } else {
            const errorData = await respuesta.json();
            alert(`❌ Error al guardar venta: ${JSON.stringify(errorData)}`);
        }

    } catch (error) {
        console.error(error);
        alert("Error de conexión");
    }
  };

  return (
    <div style={{ background: 'white', padding: '30px', borderRadius: '10px', maxWidth: '800px', margin: '20px auto', boxShadow: '0 4px 10px rgba(0,0,0,0.1)' }}>
        
        <div style={{display: 'flex', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #eee', paddingBottom: '10px'}}>
            <button onClick={volverAlInicio} style={{marginRight: '15px', cursor: 'pointer', border: 'none', background: 'transparent', fontSize: '1.5em'}}>⬅️</button>
            <h2 style={{margin: 0, color: '#9b59b6'}}>
                {modoEdicion ? '✏️ Editar Venta' : '🛒 Registrar Nueva Venta'}
            </h2>
            <span style={{marginLeft: 'auto', fontSize: '0.9em', color: '#7f8c8d'}}>{clienteInfo.nombre}</span>
        </div>
        
        {cargandoDatos && (
            <div style={{padding: '20px', textAlign: 'center', background: '#f0f0f0', borderRadius: '5px', marginBottom: '20px'}}>
                ⏳ Cargando datos de la venta...
            </div>
        )}

        {/* FILA 1 */}
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px'}}>
            <div>
                <label style={{display: 'block'}}>Tipo Documento</label>
                <select value={tipoDocumento} onChange={(e) => {
                    setTipoDocumento(e.target.value);
                    // Si cambia a CF, limpiar datos de cliente
                    if (e.target.value === "CF") {
                        setNrcCliente("");
                        setNombreCliente("");
                        setExisteCliente(false);
                        setNombreBloqueado(false);
                        setModoCrearCliente(false);
                    }
                    // Resetear montos al cambiar tipo de documento
                    setMontoGravado("");
                    setMontoIva("");
                    setMontoTotal("");
                }} style={{width: '100%', padding: '10px'}}>
                    <option value="CCF">CCF - Crédito Fiscal (Contribuyente)</option>
                    <option value="CF">CF - Consumidor Final</option>
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
                        // Limpiar error mientras escribe
                        setErrorFecha("");
                    }}
                    onBlur={handleFechaBlur}
                    style={{
                        width: '100%', 
                        padding: '8px', 
                        border: errorFecha ? '2px solid #e74c3c' : '1px solid #ccc'
                    }} 
                />
                {errorFecha && (
                    <small style={{display: 'block', color: '#e74c3c', marginTop: '5px'}}>
                        ❌ {errorFecha}
                    </small>
                )}
            </div>
        </div>
        
        {/* INFO PERÍODO (Desde barra superior) */}
        <div style={{marginBottom: '20px', padding: '10px', background: '#e8f6f3', borderRadius: '5px', fontSize: '0.9em', color: '#27ae60'}}>
            📅 Período aplicado: <strong>{periodoFormateado}</strong> (configurado en la barra superior)
        </div>

        {/* FILA 2 */}
        <div style={{marginBottom: '20px'}}>
            <label style={{display: 'block'}}>Nº Correlativo</label>
            <input value={numeroDocumento} onChange={(e) => setNumeroDocumento(e.target.value)} style={{width: '100%', padding: '10px', border: '1px solid #ccc'}} />
        </div>

        {/* CLIENTE: Solo mostrar si NO es Consumidor Final */}
        {!esConsumidorFinal && (
            <div style={{display: 'flex', gap: '10px', marginBottom: '20px', alignItems: 'center'}}>
                <div style={{width: '30%', position: 'relative'}}>
                    <input 
                        placeholder="NRC Cliente (Ej: 123456-7)" 
                        value={nrcCliente} 
                        onChange={(e) => {
                            setNrcCliente(e.target.value);
                            // Resetear estados cuando cambia el NRC
                            setExisteCliente(false);
                            setNombreBloqueado(false);
                            setModoCrearCliente(false);
                            setNombreCliente("");
                        }} 
                        onBlur={buscarCliente} 
                        style={{padding:'10px', width: '100%'}}
                        disabled={isLoadingCliente}
                    />
                    {isLoadingCliente && (
                        <span style={{position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.8em', color: '#7f8c8d'}}>
                            🔍 Buscando...
                        </span>
                    )}
                </div>
                <div style={{flex: 1, position: 'relative'}}>
                    <input 
                        placeholder={modoCrearCliente ? "Escribe el nombre del cliente" : "Nombre Cliente"} 
                        value={nombreCliente} 
                        onChange={(e)=>setNombreCliente(e.target.value)} 
                        onBlur={modoCrearCliente ? crearCliente : undefined}
                        readOnly={nombreBloqueado}
                        style={{
                            padding:'10px', 
                            width: '100%',
                            background: nombreBloqueado ? '#e9ecef' : 'white',
                            cursor: nombreBloqueado ? 'not-allowed' : 'text',
                            border: existeCliente ? '2px solid #27ae60' : '1px solid #ccc'
                        }} 
                    />
                    {existeCliente && (
                        <span style={{position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.8em', color: '#27ae60'}}>
                            ✅ Existe
                        </span>
                    )}
                    {modoCrearCliente && !existeCliente && (
                        <span style={{position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.8em', color: '#f39c12'}}>
                            ✏️ Nuevo
                        </span>
                    )}
                </div>
            </div>
        )}
        
        {/* Mensaje para Consumidor Final */}
        {esConsumidorFinal && (
            <div style={{marginBottom: '20px', padding: '15px', background: '#fff3cd', borderRadius: '5px', border: '1px solid #ffc107'}}>
                <strong>ℹ️ Consumidor Final:</strong> No se requiere cliente específico. El sistema asignará automáticamente "Consumidor Final".
            </div>
        )}

        {/* FILA 3: MONTOS */}
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '20px', background: '#fcf3cf', padding: '15px', borderRadius: '5px'}}>
            <div>
                <label style={{fontWeight: 'bold', color: '#2c3e50'}}>
                    {esConsumidorFinal ? '💰 Total (IVA Incluido)' : '📊 Base Gravada'}
                </label>
                <input 
                    type="number" 
                    step="0.01"
                    placeholder={esConsumidorFinal ? "Ej: 113.00" : "Ej: 100.00"} 
                    value={esConsumidorFinal ? montoTotal : montoGravado} 
                    onChange={handleMontoChange} 
                    style={{
                        padding:'10px', 
                        width: '100%',
                        fontSize: '1.1em',
                        fontWeight: esConsumidorFinal ? 'bold' : 'normal'
                    }} 
                />
                <small style={{display: 'block', color: '#7f8c8d', marginTop: '5px', fontSize: '0.85em'}}>
                    {esConsumidorFinal 
                        ? '✏️ Escribe el monto total que pagó el cliente (IVA incluido)' 
                        : '✏️ Escribe la base sin IVA'}
                </small>
            </div>
            <div>
                <label>Base Gravada</label>
                <input 
                    type="number" 
                    placeholder="0.00" 
                    value={montoGravado} 
                    readOnly 
                    style={{padding:'10px', width: '100%', background:'#f9e79f'}} 
                />
                <small style={{display: 'block', color: '#7f8c8d', marginTop: '5px', fontSize: '0.85em'}}>
                    {esConsumidorFinal ? '🔢 Calculado: Total ÷ 1.13' : 'Base sin IVA'}
                </small>
            </div>
            <div>
                <label>IVA (13%)</label>
                <input 
                    type="number" 
                    placeholder="0.00" 
                    value={montoIva} 
                    readOnly 
                    style={{padding:'10px', width: '100%', background:'#f9e79f'}} 
                />
                <small style={{display: 'block', color: '#7f8c8d', marginTop: '5px', fontSize: '0.85em'}}>
                    {esConsumidorFinal ? '🔢 Calculado: Total - Base' : '13% de la base'}
                </small>
            </div>
        </div>
        
        {/* Resumen visual */}
        <div style={{marginBottom: '20px', padding: '15px', background: esConsumidorFinal ? '#e8f5e9' : '#e3f2fd', borderRadius: '5px', border: `2px solid ${esConsumidorFinal ? '#27ae60' : '#2196f3'}`}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <span style={{fontSize: '0.9em', color: '#7f8c8d'}}>
                    {esConsumidorFinal ? '💡 Modo: IVA Incluido' : '💡 Modo: IVA Agregado'}
                </span>
                <strong style={{fontSize: '1.2em', color: esConsumidorFinal ? '#27ae60' : '#2196f3'}}>
                    Total: ${parseFloat(montoTotal || 0).toFixed(2)}
                </strong>
            </div>
        </div>

        <div style={{marginTop: '30px', display: 'flex', justifyContent: 'flex-end', gap: '10px'}}>
            <button onClick={() => guardarVenta(false)} style={{padding: '15px 20px', background: '#34495e', color: 'white', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer'}}>
                ➕ Guardar y Otra
            </button>
            <button onClick={() => guardarVenta(true)} style={{padding: '15px 30px', background: '#9b59b6', color: 'white', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer'}}>
                💾 Guardar y Terminar
            </button>
        </div>
    </div>
  );
};

export default FormularioVentas;