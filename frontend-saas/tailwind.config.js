/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'agil': {
          primary: '#1A56DB',
          'primary-hover': '#1644b8',
          success: '#10B981',
          orange: '#F59E0B',
          'orange-light': '#FEF3C7',
          'bg-main': '#F3F4F6',
          'bg-white': '#FFFFFF',
          'text-primary': '#1F2937',
          'text-secondary': '#6B7280',
          'border-subtle': '#E5E7EB',
        },
      },
    },
  },
  plugins: [],
}
