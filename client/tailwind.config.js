module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0d1117',
          800: '#161b22',
          700: '#21262d',
          600: '#30363d',
          500: '#484f58',
          400: '#6e7681',
        },
        accent: '#f7931a',
        'accent-hover': '#e8850f',
        'accent-soft': 'rgba(247,147,26,0.12)',
        profit: '#3fb68b',
        'profit-soft': 'rgba(63,182,139,0.12)',
        loss: '#f0616d',
        'loss-soft': 'rgba(240,97,109,0.12)',
        muted: '#8b949e',
        mint: '#7ee8c7',
        coral: '#ff9a9e',
        lavender: '#c4b5fd',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Pretendard', 'Inter', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
