/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './*/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        // NetExpress brand colors (green theme #0e6b4c)
        'ne-primary': {
          50: '#e6f5f0',
          100: '#cceae1',
          200: '#99d5c3',
          300: '#66c0a5',
          400: '#33ab87',
          500: '#0e6b4c',
          600: '#0c5a40',
          700: '#0a4934',
          800: '#083828',
          900: '#06271c',
        },
        'ne-secondary': {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        }
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}