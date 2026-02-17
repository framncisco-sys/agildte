# Frontend SaaS - Facturación Electrónica

Proyecto React moderno con Vite, Tailwind, Zustand, React Router y formularios con React Hook Form + Zod.

## Tech Stack

- **Vite** - Build tool
- **Tailwind CSS** - Estilos y diseño responsive
- **React Router DOM** - Enrutamiento
- **Zustand** - Estado global (Auth, Empresa)
- **Axios** - Cliente API con interceptores
- **React Hook Form + Zod** - Formularios y validación

## Comandos

```bash
# Instalar dependencias
npm install

# Copiar variables de entorno
copy .env.example .env

# Desarrollo
npm run dev

# Build
npm run build

# Preview del build
npm run preview
```

## Estructura

```
src/
├── api/           # axios.js - cliente con interceptores (token, X-Company-ID)
├── assets/
├── components/    # UI reutilizable
├── features/      # Módulos de negocio
│   ├── auth/      # Login, etc.
│   ├── dashboard/
│   ├── facturacion/  # Migrar lógica desde frontend/
│   └── contabilidad/
├── hooks/
├── layouts/       # MainLayout, AuthLayout
├── router/        # Rutas y RequireAuth
├── stores/        # useAuthStore, useEmpresaStore
└── utils/         # format.js (moneda, fechas)
```

## Rutas

- `/login` - Inicio de sesión (pública)
- `/dashboard` - Dashboard (protegida)
- `/facturacion` - Facturación (protegida)
- `/facturacion/nueva` - Nueva factura (protegida)
- `/facturacion/lista` - Lista de facturas (protegida)
- `/contabilidad` - Contabilidad (protegida)

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `VITE_API_BASE_URL` | URL base del API (ej: http://localhost:8000/api) |
