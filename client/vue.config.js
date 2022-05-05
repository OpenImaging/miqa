const fs = require('fs');
const util = require('util');
const webpack = require('webpack');
const CopyPlugin = require('copy-webpack-plugin');
const path = require('path');
const vtkChainWebpack = require('vtk.js/Utilities/config/chainWebpack');
const packageJson = require('./package.json');

const stat = util.promisify(fs.stat);

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
            filter: async (resourcePath) => {
              const resourceStats = await stat(resourcePath);
              const resourceSize = resourceStats.size;
              // Exclude files larger than 25MB.
              // Cloudflare Pages does not allow assets larger than this:
              // https://developers.cloudflare.com/pages/platform/limits/#file-size
              // In a typical library, module resolution is handled by the bundler (Webpack, Parcel,
              // etc.), which can perform tree shaking to exclude unused content from the final
              // build and can make choices as to how to split and potentially asynchronously load
              // built modules. See: https://webpack.js.org/guides/code-splitting/
              // However, itk.js instead internally implements its own runtime asynchronous module
              // loader:
              // https://github.com/InsightSoftwareConsortium/itk-wasm/blob/v14.0.0/src/loadEmscriptenModuleBrowser.js
              // and expects the build system to copy the entire itk.js library to the output
              // directory:
              // https://github.com/InsightSoftwareConsortium/itk-wasm/blob/v14.0.0/doc/content/examples/webpack.md
              // Even if the bundler performs tree-shaking of the actual pure-Javascript code paths
              // through itk.js, it's impossible to know what other files might be internally
              // fetched by itk.js dynamically at runtime.
              // So, here we'll copy everything by default, but exclude the largest files to
              // make this application deployable, and hope that none of the excluded files were
              // actually necessary at runtime.
              // With itk@14.0.0, only "itk/PolyDataIOs/VTKExodusFileReader.js" is actually
              // excluded.
              // The semantics of "CopyPlugin.filter" are the same as "Array.prototype.filter".
              return resourceSize <= (25 * 1024 * 1024);
            },
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
