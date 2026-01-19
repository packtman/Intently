/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep space theme - unique dark aesthetic
        void: {
          50: '#f0f4ff',
          100: '#e0e8ff',
          200: '#c7d4fe',
          300: '#a5b8fc',
          400: '#8194f8',
          500: '#6571f1',
          600: '#4f4ce5',
          700: '#413dca',
          800: '#1a1a2e',
          900: '#0f0f1a',
          950: '#07070d',
        },
        // Cyan accent for highlights
        neon: {
          50: '#ecfffe',
          100: '#cefffe',
          200: '#a3fffc',
          300: '#63fff8',
          400: '#1cf5ed',
          500: '#00d9d4',
          600: '#00afb0',
          700: '#048a8d',
          800: '#0a6d71',
          900: '#0d5a5e',
          950: '#003a3e',
        },
        // Warm accent for warnings/actions
        ember: {
          50: '#fff8ed',
          100: '#ffefd4',
          200: '#ffdba8',
          300: '#ffc171',
          400: '#ff9c38',
          500: '#ff7d11',
          600: '#f06107',
          700: '#c74808',
          800: '#9e3a0f',
          900: '#7f3210',
          950: '#451606',
        },
        // Purple for special elements
        aurora: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',
          600: '#9333ea',
          700: '#7e22ce',
          800: '#6b21a8',
          900: '#581c87',
          950: '#3b0764',
        },
      },
      fontFamily: {
        display: ['Outfit', 'system-ui', 'sans-serif'],
        body: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 3s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gradient': 'gradient 8s linear infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 20px rgba(0, 217, 212, 0.3)' },
          '100%': { boxShadow: '0 0 40px rgba(0, 217, 212, 0.6)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(99, 255, 248, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(99, 255, 248, 0.03) 1px, transparent 1px)',
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
      },
      backgroundSize: {
        'grid': '50px 50px',
      },
    },
  },
  plugins: [],
}

