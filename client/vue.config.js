const webpack = require('webpack');
const CopyPlugin = require('copy-webpack-plugin');
const path = require('path');
const vtkChainWebpack = require('vtk.js/Utilities/config/chainWebpack');
const packageJson = require('./package.json');

module.exports = {
  devServer: {
    port: 8081,
    public: process.env.PUBLIC_ADDRESS,
  },
  lintOnSave: false,
  publicPath: process.env.VUE_APP_STATIC_PATH,
  configureWebpack: {
    plugins: [
      new CopyPlugin([
        {
          from: path.join(__dirname, 'node_modules', 'itk'),
          to: 'itk',
        },
      ]),
      new webpack.DefinePlugin({
        'process.env': {
          VERSION: JSON.stringify(packageJson.version),
        },
      }),
    ],
  },
  chainWebpack: (config) => {
    vtkChainWebpack(config);
  },
};
