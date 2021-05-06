// This is a minimal config.
// If you need the full config, get it from here:
// https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
const colors = require('tailwindcss/colors')

module.exports = {
  purge: [
    // If source HTML files are ever added to this project in another directory, include them here
    './_includes/**/*.html',
    './_layouts/**/*.html',
  ],
  darkMode: false, // or 'media' or 'class'
  theme: {
    fontFamily: {
      'sans': '"Manrope", sans-serif'
    },
    extend: {
      colors: {
        'accent': {
          '50': '#fdf5f5',
          '100': '#fbebea',
          '200': '#f5cecb',
          '300': '#efb0ab',
          '400': '#e4746d',
          '500': '#d8392e',
          '600': '#c23329',
          '700': '#a22b23',
          '800': '#82221c',
          '900': '#6a1c17'
        }, 'secondary': {
          '50': '#f6f6f6',
          '100': '#ececec',
          '200': '#d0d0d0',
          '300': '#b3b3b3',
          '400': '#7b7b7b',
          '500': '#424242',
          '600': '#3b3b3b',
          '700': '#323232',
          '800': '#282828',
          '900': '#202020'
        }, 'primary': {
          '50': '#f2fafd',
          '100': '#e6f5fb',
          '200': '#bfe5f6',
          '300': '#99d5f0',
          '400': '#4db6e4',
          '500': '#0097d9', //actual logo color
          '600': '#0088c3',
          '700': '#0071a3',
          '800': '#005b82',
          '900': '#004a6a'
        }
      },
      fontSize: {
        '2xs': '.7rem',
        '3xs': '.63rem',
      },
      maxWidth: {
        '2xs': '16rem',
        '3xs': '12rem',
      },
      minWidth: {
        '2xs': '16rem',
        '3xs': '12rem',
      },
      textShadow: {
        '2xl': '0 2px 6px rgba(0, 0, 0, .38), 0 2px 20px rgba(0, 0, 0, .22)',
      },
    },
  },
  variants: {
    extend: {
      borderWidth: ['hover', 'focus', 'group-hover', 'group-focus', 'last'],
      display: ['hover', 'focus', 'group-hover', 'group-focus'],
    },
  },
  plugins: [
    require('tailwindcss-textshadow')
  ],
}
