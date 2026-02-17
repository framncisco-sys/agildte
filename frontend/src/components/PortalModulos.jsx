import React from 'react';

const PortalModulos = ({ empresa, onSeleccionarModulo, onCambiarEmpresa }) => {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      {/* Header */}
      <div style={{
        background: 'white',
        borderRadius: '15px',
        padding: '30px',
        marginBottom: '30px',
        boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
        textAlign: 'center',
        maxWidth: '600px',
        width: '100%'
      }}>
        <h1 style={{ margin: '0 0 10px 0', color: '#2c3e50', fontSize: '2em' }}>
          🏢 Sistema Contable
        </h1>
        <p style={{ margin: '0 0 20px 0', color: '#7f8c8d', fontSize: '1.1em' }}>
          Empresa: <strong style={{ color: '#667eea' }}>{empresa.nombre}</strong>
        </p>
        <button
          onClick={onCambiarEmpresa}
          style={{
            padding: '8px 20px',
            background: '#95a5a6',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            fontSize: '0.9em'
          }}
        >
          🔄 Cambiar Empresa
        </button>
      </div>

      {/* Tarjetas de Módulos */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '30px',
        maxWidth: '900px',
        width: '100%'
      }}>
        {/* Módulo Facturación */}
        <div
          onClick={() => onSeleccionarModulo('facturacion')}
          style={{
            background: 'white',
            borderRadius: '15px',
            padding: '40px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
            cursor: 'pointer',
            transition: 'all 0.3s',
            textAlign: 'center',
            border: '3px solid transparent'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-10px)';
            e.currentTarget.style.borderColor = '#3498db';
            e.currentTarget.style.boxShadow = '0 15px 40px rgba(52, 152, 219, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.borderColor = 'transparent';
            e.currentTarget.style.boxShadow = '0 10px 30px rgba(0,0,0,0.2)';
          }}
        >
          <div style={{ fontSize: '5em', marginBottom: '20px' }}>🧾</div>
          <h2 style={{ margin: '0 0 15px 0', color: '#2c3e50', fontSize: '1.8em' }}>
            Facturación e Ingresos
          </h2>
          <p style={{ margin: '0 0 20px 0', color: '#7f8c8d', fontSize: '1em', lineHeight: '1.6' }}>
            Emite facturas electrónicas (DTE), gestiona clientes y controla tus ingresos.
          </p>
          <div style={{
            padding: '12px 25px',
            background: '#3498db',
            color: 'white',
            borderRadius: '8px',
            fontWeight: 'bold',
            fontSize: '1.1em',
            display: 'inline-block'
          }}>
            → Ingresar
          </div>
        </div>

        {/* Módulo Contabilidad */}
        <div
          onClick={() => onSeleccionarModulo('contabilidad')}
          style={{
            background: 'white',
            borderRadius: '15px',
            padding: '40px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
            cursor: 'pointer',
            transition: 'all 0.3s',
            textAlign: 'center',
            border: '3px solid transparent'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-10px)';
            e.currentTarget.style.borderColor = '#27ae60';
            e.currentTarget.style.boxShadow = '0 15px 40px rgba(39, 174, 96, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.borderColor = 'transparent';
            e.currentTarget.style.boxShadow = '0 10px 30px rgba(0,0,0,0.2)';
          }}
        >
          <div style={{ fontSize: '5em', marginBottom: '20px' }}>📊</div>
          <h2 style={{ margin: '0 0 15px 0', color: '#2c3e50', fontSize: '1.8em' }}>
            Contabilidad e Impuestos
          </h2>
          <p style={{ margin: '0 0 20px 0', color: '#7f8c8d', fontSize: '1em', lineHeight: '1.6' }}>
            Libros de compras, ventas, retenciones y generación de anexos para el Ministerio de Hacienda.
          </p>
          <div style={{
            padding: '12px 25px',
            background: '#27ae60',
            color: 'white',
            borderRadius: '8px',
            fontWeight: 'bold',
            fontSize: '1.1em',
            display: 'inline-block'
          }}>
            → Ingresar
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        marginTop: '40px',
        color: 'white',
        textAlign: 'center',
        fontSize: '0.9em',
        opacity: 0.9
      }}>
        <p>Selecciona el módulo que deseas utilizar</p>
      </div>
    </div>
  );
};

export default PortalModulos;






