/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0b1220',
        surface: '#111827',
        panel: '#161e35',
        brand: {
          DEFAULT: '#38bdf8',
          secondary: '#818cf8',
        },
        muted: '#94a3b8',
        success: '#34d399',
        warning: '#fbbf24',
        danger: '#fb7185',
        'text-high': '#f8fafc',
        'text-muted': '#94a3b8',
      },
      borderColor: {
        studio: 'rgba(148, 163, 184, 0.18)',
      },
      ringColor: {
        studio: 'rgba(148, 163, 184, 0.18)',
      },
      boxShadow: {
        'soft-glow': '0 0 40px rgba(56, 189, 248, 0.18)',
        'soft-glow-hover': '0 0 48px rgba(129, 140, 248, 0.16)',
        panel: '0 30px 60px -30px rgba(15, 23, 42, 0.8)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.35s ease-out forwards',
      },
    },
  },
  plugins: [],
};
