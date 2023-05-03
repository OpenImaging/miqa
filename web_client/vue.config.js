const webpack = require('webpack');
const vtkChainWebpack = require('vtk.js/Utilities/config/chainWebpack');
const packageJson = require('./package.json');

module.exports = {
  devServer: {
    port: 8081,
    host: process.env.PUBLIC_ADDRESS,
  },
  lintOnSave: false,
  publicPath: process.env.VUE_APP_STATIC_PATH,
  configureWebpack: {
    plugins: [
      new webpack.DefinePlugin({
        'process.env': {
          VERSION: JSON.stringify(packageJson.version),
        },
      }),
    ],
    performance: {
      maxEntrypointSize: 4000000,
      maxAssetSize: 40000000,

    },
  },
  chainWebpack: (config) => {
    vtkChainWebpack(config);
  },
};
