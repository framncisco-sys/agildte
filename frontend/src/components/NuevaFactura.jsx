import React, { useState, useEffect } from 'react';
import { usePeriodo } from '../contexts/PeriodoContext';

const NuevaFactura = ({ empresa, ventaId, volverAlInicio }) => {
  const { periodoFormateado } = usePeriodo();
  
  // Estados del formulario
  const [fechaEmision, setFechaEmision] = useState(new Date().toISOString().split('T')[0]);
  const [tipoVenta, setTipoVenta] = useState('CCF');
  const [nrcCliente, setNrcCliente] = useState('');
  const [nombreCliente, setNombreCliente] = useState('');
  const [items, setItems] = useState([]);
  const [productos, setProductos] = useState([]);
  const [buscadorProducto, setBuscadorProducto] = useState('');
  const [productosFiltrados, setProductosFiltrados] = useState([]);
  const [mostrarBuscador, setMostrarBuscador] = useState(false);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    cargarProductos();
  }, [empresa]);

  // Función auxiliar para redondear a 2 decimales (debe estar antes de usarse)
  const redondearADosDecimales = (valor) => {
    const num = parseFloat(valor) || 0;
    return Math.round(num * 100) / 100;
  };

  const cargarProductos = async () => {
    if (!empresa?.id) return;
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/productos/?empresa_id=${empresa.id}`);
      if (response.ok) {
        const data = await response.json();
        setProductos(Array.isArray(data) ? data : (data.results || []));
      }
    } catch (err) {
      console.error('Error cargando productos:', err);
    }
  };

  const agregarItem = (producto = null) => {
    const precioBase = producto ? parseFloat(producto.precio_unitario) : 0;
    const precioRedondeado = redondearADosDecimales(precioBase);
    
    const nuevoItem = {
      id: Date.now(),
      producto_id: producto?.id || null,
      codigo: producto?.codigo || '',
      descripcion: producto?.descripcion || '',
      cantidad: 1,
      precio_unitario: precioRedondeado,
      tipo_item: producto?.tipo_item || 1,
      monto_descuento: 0,
      venta_no_sujeta: 0,
      venta_exenta: 0,
      venta_gravada: precioRedondeado,
      iva_item: 0
    };
    
    // Calcular IVA si hay venta gravada
    if (nuevoItem.venta_gravada > 0) {
      nuevoItem.iva_item = redondearADosDecimales(nuevoItem.venta_gravada * 0.13);
    }
    
    setItems([...items, nuevoItem]);
    setMostrarBuscador(false);
    setBuscadorProducto('');
  };

  const eliminarItem = (itemId) => {
    setItems(items.filter(item => item.id !== itemId));
  };

  const actualizarItem = (itemId, campo, valor) => {
    setItems(items.map(item => {
      if (item.id === itemId) {
        const actualizado = { ...item, [campo]: redondearADosDecimales(valor) };
        
        // Recalcular subtotal y IVA
        if (campo === 'cantidad' || campo === 'precio_unitario' || campo === 'monto_descuento') {
          const subtotal = redondearADosDecimales(
            (actualizado.cantidad * actualizado.precio_unitario) - actualizado.monto_descuento
          );
          actualizado.venta_gravada = subtotal;
          actualizado.iva_item = redondearADosDecimales(subtotal * 0.13);
        }
        
        return actualizado;
      }
      return item;
    }));
  };

  const calcularTotales = () => {
    const totales = items.reduce((acc, item) => {
      acc.venta_gravada += item.venta_gravada || 0;
      acc.venta_exenta += item.venta_exenta || 0;
      acc.venta_no_sujeta += item.venta_no_sujeta || 0;
      acc.iva += item.iva_item || 0;
      return acc;
    }, { venta_gravada: 0, venta_exenta: 0, venta_no_sujeta: 0, iva: 0 });
    
    // Redondear todos los totales a 2 decimales
    totales.venta_gravada = redondearADosDecimales(totales.venta_gravada);
    totales.venta_exenta = redondearADosDecimales(totales.venta_exenta);
    totales.venta_no_sujeta = redondearADosDecimales(totales.venta_no_sujeta);
    totales.iva = redondearADosDecimales(totales.iva);
    totales.total = redondearADosDecimales(
      totales.venta_gravada + totales.venta_exenta + totales.venta_no_sujeta + totales.iva
    );
    return totales;
  };

  const buscarCliente = async () => {
    if (!nrcCliente) return;
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/clientes/?nrc=${nrcCliente}`);
      if (response.ok) {
        const data = await response.json();
        if (data.length > 0) {
          setNombreCliente(data[0].nombre);
        }
      }
    } catch (err) {
      console.error('Error buscando cliente:', err);
    }
  };

  const filtrarProductos = (termino) => {
    setBuscadorProducto(termino);
    if (termino) {
      const filtrados = productos.filter(p => 
        p.codigo.toLowerCase().includes(termino.toLowerCase()) ||
        p.descripcion.toLowerCase().includes(termino.toLowerCase())
      );
      setProductosFiltrados(filtrados);
      setMostrarBuscador(true);
    } else {
      setMostrarBuscador(false);
    }
  };

  const guardarYEmitir = async () => {
    if (items.length === 0) {
      alert('⚠️ Debes agregar al menos un item a la factura');
      return;
    }

    if (tipoVenta === 'CCF' && !nrcCliente) {
      alert('⚠️ Debes proporcionar el NRC del cliente para facturas a Contribuyentes');
      return;
    }

    setGuardando(true);

    try {
      const totales = calcularTotales();
      
      // Función auxiliar para redondear a 2 decimales y convertir a string con formato
      const redondearParaEnvio = (valor) => {
        const num = parseFloat(valor) || 0;
        return parseFloat(num.toFixed(2));
      };
      
      // Crear la venta con valores redondeados
      const ventaData = {
        empresa: empresa.id,
        cliente: tipoVenta === 'CF' ? null : nrcCliente,
        fecha_emision: fechaEmision,
        periodo_aplicado: periodoFormateado,
        tipo_venta: tipoVenta,
        nombre_receptor: tipoVenta === 'CF' ? 'Consumidor Final' : nombreCliente,
        nrc_receptor: tipoVenta === 'CF' ? '0000-000000-000-0' : nrcCliente,
        venta_gravada: redondearParaEnvio(totales.venta_gravada),
        venta_exenta: redondearParaEnvio(totales.venta_exenta),
        venta_no_sujeta: redondearParaEnvio(totales.venta_no_sujeta),
        debito_fiscal: redondearParaEnvio(totales.iva),
        estado_dte: 'Generado',
        clase_documento: '4',
        clasificacion_venta: '1',
        tipo_ingreso: '3',
        detalles: items.map((item, index) => ({
          producto_id: item.producto_id,
          descripcion_libre: item.producto_id ? null : item.descripcion,
          codigo_libre: item.producto_id ? null : item.codigo,
          cantidad: redondearParaEnvio(item.cantidad),
          precio_unitario: redondearParaEnvio(item.precio_unitario),
          monto_descuento: redondearParaEnvio(item.monto_descuento),
          venta_no_sujeta: redondearParaEnvio(item.venta_no_sujeta),
          venta_exenta: redondearParaEnvio(item.venta_exenta),
          venta_gravada: redondearParaEnvio(item.venta_gravada),
          iva_item: redondearParaEnvio(item.iva_item),
          numero_item: index + 1
        }))
      };

      const response = await fetch('http://127.0.0.1:8000/api/ventas/crear-con-detalles/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ventaData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Error al guardar la factura');
      }

      const data = await response.json();
      alert('✅ Factura guardada y DTE generado exitosamente');
      volverAlInicio();
    } catch (error) {
      alert(`❌ Error: ${error.message}`);
    } finally {
      setGuardando(false);
    }
  };

  const totales = calcularTotales();

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h2 style={{ margin: 0, color: '#2c3e50' }}>🧾 Nueva Factura</h2>
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

      {/* FORMULARIO PRINCIPAL */}
      <div style={{ background: 'white', borderRadius: '10px', padding: '30px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Fecha Emisión</label>
            <input
              type="date"
              value={fechaEmision}
              onChange={(e) => setFechaEmision(e.target.value)}
              style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Tipo de Venta</label>
            <select
              value={tipoVenta}
              onChange={(e) => {
                setTipoVenta(e.target.value);
                if (e.target.value === 'CF') {
                  setNrcCliente('');
                  setNombreCliente('');
                }
              }}
              style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
            >
              <option value="CCF">CCF - Contribuyente</option>
              <option value="CF">CF - Consumidor Final</option>
            </select>
          </div>
          {tipoVenta === 'CCF' && (
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>NRC Cliente</label>
              <div style={{ display: 'flex', gap: '5px' }}>
                <input
                  type="text"
                  value={nrcCliente}
                  onChange={(e) => setNrcCliente(e.target.value)}
                  onBlur={buscarCliente}
                  placeholder="Ej: 123456-7"
                  style={{ flex: 1, padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
                />
              </div>
              {nombreCliente && (
                <small style={{ color: '#27ae60', marginTop: '5px', display: 'block' }}>✓ {nombreCliente}</small>
              )}
            </div>
          )}
        </div>
      </div>

      {/* TABLA DE ITEMS */}
      <div style={{ background: 'white', borderRadius: '10px', padding: '30px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0, color: '#2c3e50' }}>Items de la Factura</h3>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              placeholder="🔍 Buscar producto..."
              value={buscadorProducto}
              onChange={(e) => filtrarProductos(e.target.value)}
              onFocus={() => setMostrarBuscador(true)}
              style={{
                padding: '10px 15px',
                border: '1px solid #ddd',
                borderRadius: '5px',
                width: '300px'
              }}
            />
            {mostrarBuscador && productosFiltrados.length > 0 && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                background: 'white',
                border: '1px solid #ddd',
                borderRadius: '5px',
                marginTop: '5px',
                maxHeight: '200px',
                overflow: 'auto',
                zIndex: 1000,
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
              }}>
                {productosFiltrados.map(producto => (
                  <div
                    key={producto.id}
                    onClick={() => agregarItem(producto)}
                    style={{
                      padding: '10px',
                      cursor: 'pointer',
                      borderBottom: '1px solid #eee'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f8f9fa'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                  >
                    <strong>{producto.codigo}</strong> - {producto.descripcion} - ${parseFloat(producto.precio_unitario).toFixed(2)}
                  </div>
                ))}
              </div>
            )}
            <button
              onClick={() => agregarItem()}
              style={{
                marginLeft: '10px',
                padding: '10px 20px',
                background: '#27ae60',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
                fontWeight: 'bold'
              }}
            >
              ➕ Item Libre
            </button>
          </div>
        </div>

        {items.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#7f8c8d' }}>
            <p>No hay items agregados. Busca un producto o agrega un item libre.</p>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#34495e', color: 'white' }}>
                <th style={{ padding: '10px', textAlign: 'left' }}>Código</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Descripción</th>
                <th style={{ padding: '10px', textAlign: 'center' }}>Cantidad</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Precio Unit.</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Descuento</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Subtotal</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>IVA</th>
                <th style={{ padding: '10px', textAlign: 'center' }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={item.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '10px' }}>
                    <input
                      type="text"
                      value={item.codigo}
                      onChange={(e) => {
                        const nuevo = { ...item, codigo: e.target.value };
                        setItems(items.map(i => i.id === item.id ? nuevo : i));
                      }}
                      style={{ width: '100px', padding: '5px', border: '1px solid #ddd', borderRadius: '3px' }}
                    />
                  </td>
                  <td style={{ padding: '10px' }}>
                    <input
                      type="text"
                      value={item.descripcion}
                      onChange={(e) => {
                        const nuevo = { ...item, descripcion: e.target.value };
                        setItems(items.map(i => i.id === item.id ? nuevo : i));
                      }}
                      style={{ width: '100%', padding: '5px', border: '1px solid #ddd', borderRadius: '3px' }}
                    />
                  </td>
                  <td style={{ padding: '10px', textAlign: 'center' }}>
                    <input
                      type="number"
                      step="0.01"
                      value={item.cantidad}
                      onChange={(e) => actualizarItem(item.id, 'cantidad', e.target.value)}
                      style={{ width: '80px', padding: '5px', border: '1px solid #ddd', borderRadius: '3px' }}
                    />
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    <input
                      type="number"
                      step="0.01"
                      value={item.precio_unitario}
                      onChange={(e) => actualizarItem(item.id, 'precio_unitario', e.target.value)}
                      style={{ width: '100px', padding: '5px', border: '1px solid #ddd', borderRadius: '3px' }}
                    />
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    <input
                      type="number"
                      step="0.01"
                      value={item.monto_descuento}
                      onChange={(e) => actualizarItem(item.id, 'monto_descuento', e.target.value)}
                      style={{ width: '100px', padding: '5px', border: '1px solid #ddd', borderRadius: '3px' }}
                    />
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right', fontWeight: 'bold' }}>
                    ${((item.cantidad * item.precio_unitario) - item.monto_descuento).toFixed(2)}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    ${item.iva_item.toFixed(2)}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'center' }}>
                    <button
                      onClick={() => eliminarItem(item.id)}
                      style={{
                        padding: '5px 10px',
                        background: '#e74c3c',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: 'pointer'
                      }}
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* RESUMEN Y BOTÓN */}
      <div style={{ background: 'white', borderRadius: '10px', padding: '30px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
          <div>
            <h4 style={{ margin: '0 0 15px 0', color: '#2c3e50' }}>Resumen</h4>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <span>Venta Gravada:</span>
              <strong>${totales.venta_gravada.toFixed(2)}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <span>IVA (13%):</span>
              <strong>${totales.iva.toFixed(2)}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', paddingTop: '10px', borderTop: '2px solid #eee' }}>
              <span style={{ fontSize: '1.2em', fontWeight: 'bold' }}>Total:</span>
              <span style={{ fontSize: '1.2em', fontWeight: 'bold', color: '#27ae60' }}>
                ${totales.total.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
        <button
          onClick={guardarYEmitir}
          disabled={guardando || items.length === 0}
          style={{
            width: '100%',
            padding: '15px',
            background: guardando || items.length === 0 ? '#95a5a6' : '#27ae60',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: guardando || items.length === 0 ? 'not-allowed' : 'pointer',
            fontWeight: 'bold',
            fontSize: '1.1em'
          }}
        >
          {guardando ? '⏳ Guardando y Emitiendo...' : '💾 Guardar y Emitir DTE'}
        </button>
      </div>
    </div>
  );
};

export default NuevaFactura;

