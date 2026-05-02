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
        background: 'var(--bg)',
        surface: 'var(--surface)',
        panel: 'var(--panel)',
        brand: {
          DEFAULT: 'var(--brand)',
          secondary: 'var(--brand-secondary)',
        },
        muted: 'var(--text-muted)',
        success: 'var(--success)',
        warning: 'var(--warning)',
        danger: 'var(--danger)',
        'text-high': 'var(--text)',
        'text-muted': 'var(--text-muted)',
      },
      borderColor: {
        studio: 'var(--border-subtle)',
      },
      ringColor: {
        studio: 'var(--border-subtle)',
      },
      boxShadow: {
        'soft-glow': '0 0 40px var(--shadow-glow)',
        'soft-glow-hover': '0 0 48px var(--shadow-glow-strong)',
        panel: '0 30px 60px -30px var(--shadow-panel)',
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
