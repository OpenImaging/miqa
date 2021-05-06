module.exports = {
    plugins: {
      tailwindcss: { config: 'tailwind.config.js' },
    },
    plugins: [
        require('tailwindcss'),
        require('cssnano')(),
        require('autoprefixer'),
    ]
};
