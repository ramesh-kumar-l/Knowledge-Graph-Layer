/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#141415',
        canvas: '#0a0a0b',
        border: '#27272a',
        muted: '#71717a',
      },
    },
  },
  plugins: [],
};
