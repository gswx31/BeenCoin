module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0b0e11',
          800: '#12161c',
          700: '#1e2329',
          600: '#2b3139',
          500: '#474d57',
          400: '#5e6673',
        },
        accent: '#f0b90b',
        'accent-hover': '#d4a30a',
        profit: '#0ecb81',
        'profit-bg': 'rgba(14,203,129,0.1)',
        loss: '#f6465d',
        'loss-bg': 'rgba(246,70,93,0.1)',
        muted: '#848e9c',
        'text-primary': '#eaecef',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
