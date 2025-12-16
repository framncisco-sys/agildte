import React, { createContext, useContext, useState, useEffect } from 'react';

const PeriodoContext = createContext();

export const usePeriodo = () => {
  const context = useContext(PeriodoContext);
  if (!context) {
    throw new Error('usePeriodo debe usarse dentro de PeriodoProvider');
  }
  return context;
};

export const PeriodoProvider = ({ children }) => {
  // Lógica de inicio inteligente: calcular mes por defecto
  const calcularMesInicial = () => {
    const hoy = new Date();
    const dia = hoy.getDate();
    const mes = hoy.getMonth() + 1; // 1-12
    const anio = hoy.getFullYear();
    
    // Si es día 1 al 10: Mes Anterior
    // Si es día 11 en adelante: Mes Actual
    if (dia >= 1 && dia <= 10) {
      // Mes anterior
      if (mes === 1) {
        return { mes: 12, anio: anio - 1 };
      } else {
        return { mes: mes - 1, anio };
      }
    } else {
      // Mes actual
      return { mes, anio };
    }
  };

  const mesInicial = calcularMesInicial();
  
  const [mes, setMes] = useState(mesInicial.mes);
  const [anio, setAnio] = useState(mesInicial.anio);
  const [empresaSeleccionada, setEmpresaSeleccionada] = useState(null);

  // Formatear período como "YYYY-MM"
  const periodoFormateado = `${anio}-${String(mes).padStart(2, '0')}`;

  const value = {
    mes,
    anio,
    empresaSeleccionada,
    periodoFormateado,
    setMes,
    setAnio,
    setEmpresaSeleccionada,
  };

  return (
    <PeriodoContext.Provider value={value}>
      {children}
    </PeriodoContext.Provider>
  );
};

