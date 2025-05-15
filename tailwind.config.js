
module.exports = {
  content: [
    "./templates/**/*.{html,js}",
    "./static/**/*.{js,css}",
    "./**/*.{html,js,py}"
  ],
  safelist: [
    'text-shopify-purple',
    'bg-shopify-purple',
    'focus:border-shopify-purple',
    'hover:bg-shopify-purple',
    'hover:border-shopify-purple'
  ],
  theme: {
    extend: {
      colors: {
        'shopify-purple': '#5c6ac4',
      }
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
