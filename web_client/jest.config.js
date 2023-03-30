module.exports = {
  preset: '@vue/cli-plugin-unit-jest/presets/typescript-and-babel',
  transformIgnorePatterns: [
    'node_modules/(?!(vtk.js|itk|@girder/oauth-client|django-s3-file-field|d3-scale|d3-array|internmap|d3-.*)/)',
  ],
  moduleNameMapper: {
    '^.+.(vert|frag|glsl)$': 'jest-transform-stub',
  },
};
