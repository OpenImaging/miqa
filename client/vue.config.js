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
      new CopyPlugin({
        patterns: [
          {
            // It'd be preferable to "require.resolve" here, to ensure that the package resolved by
            // imports matches these copied assets, but itk.js has a buggy "package.json" with an
            // invalid "main" field, which causes warnings on every build.
            from: path.join(__dirname, 'node_modules', 'itk'),
            to: 'itk',
          },
        ],
      }),
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
