import vtk2DView from 'vtk.js/Sources/Proxy/Core/View2DProxy';
import vtkGeometryRepresentationProxy from 'vtk.js/Sources/Proxy/Representations/GeometryRepresentationProxy';
import vtkSkyboxRepresentationProxy from 'vtk.js/Sources/Proxy/Representations/SkyboxRepresentationProxy';
import vtkGlyphRepresentationProxy from 'vtk.js/Sources/Proxy/Representations/GlyphRepresentationProxy';
import vtkLookupTableProxy from 'vtk.js/Sources/Proxy/Core/LookupTableProxy';
import vtkMoleculeRepresentationProxy from 'vtk.js/Sources/Proxy/Representations/MoleculeRepresentationProxy';
import vtkPiecewiseFunctionProxy from 'vtk.js/Sources/Proxy/Core/PiecewiseFunctionProxy';
import vtkProxySource from 'vtk.js/Sources/Proxy/Core/SourceProxy';
import vtkSliceRepresentationProxy from 'vtk.js/Sources/Proxy/Representations/SliceRepresentationProxy';
import vtkView from 'vtk.js/Sources/Proxy/Core/ViewProxy';
import vtkVolumeRepresentationProxy from 'vtk.js/Sources/Proxy/Representations/VolumeRepresentationProxy';

import ConfigUtils from './configUtils';

import proxyUI from './proxyUI';
import proxyLinks from './proxyLinks';
import proxyFilter from './proxyFilter';
import proxyViewRepresentationMapping from './proxyViewRepresentationMapping';

const { createProxyDefinition, activateOnCreate } = ConfigUtils;

function createDefaultView(classFactory, ui, options, props) {
  return activateOnCreate(
    createProxyDefinition(
      classFactory,
      ui,
      [
        {
          type: 'application',
          link: 'AnnotationOpacity',
          property: 'annotationOpacity',
          updateOnBind: true,
        },
        {
          type: 'application',
          link: 'OrientationAxesVisibility',
          property: 'orientationAxesVisibility',
          updateOnBind: true,
        },
        {
          type: 'application',
          link: 'OrientationAxesPreset',
          property: 'presetToOrientationAxes',
          updateOnBind: true,
        },
        {
          type: 'application',
          link: 'OrientationAxesType',
          property: 'orientationAxesType',
          updateOnBind: true,
        },
      ],
      options,
      props,
    ),
  );
}

// ----------------------------------------------------------------------------
export default {
  definitions: {
    Proxy: {
      LookupTable: createProxyDefinition(vtkLookupTableProxy, [], [], {
        presetName: 'Default (Cool to Warm)',
      }),
      PiecewiseFunction: createProxyDefinition(vtkPiecewiseFunctionProxy),
    },
    Sources: {
      TrivialProducer: activateOnCreate(createProxyDefinition(vtkProxySource)),
      Contour: proxyFilter.Contour,
    },
    Representations: {
      Geometry: createProxyDefinition(
        vtkGeometryRepresentationProxy,
        proxyUI.Geometry,
        proxyLinks.Geometry,
      ),
      Skybox: createProxyDefinition(
        vtkSkyboxRepresentationProxy,
        proxyUI.Skybox,
        proxyLinks.Skybox,
      ),
      Slice: createProxyDefinition(
        vtkSliceRepresentationProxy,
        proxyUI.Slice,
        proxyLinks.Slice,
      ),
      SliceX: createProxyDefinition(
        vtkSliceRepresentationProxy,
        proxyUI.Slice,
        [{ link: 'SliceX', property: 'slice', updateOnBind: true }].concat(
          proxyLinks.Slice,
        ),
      ),
      SliceY: createProxyDefinition(
        vtkSliceRepresentationProxy,
        proxyUI.Slice,
        [{ link: 'SliceY', property: 'slice', updateOnBind: true }].concat(
          proxyLinks.Slice,
        ),
      ),
      SliceZ: createProxyDefinition(
        vtkSliceRepresentationProxy,
        proxyUI.Slice,
        [{ link: 'SliceZ', property: 'slice', updateOnBind: true }].concat(
          proxyLinks.Slice,
        ),
      ),
      Volume: createProxyDefinition(
        vtkVolumeRepresentationProxy,
        proxyUI.Volume,
        proxyLinks.Volume,
      ),
      Molecule: createProxyDefinition(
        vtkMoleculeRepresentationProxy,
        proxyUI.Molecule,
        proxyLinks.Molecule,
      ),
      Glyph: createProxyDefinition(
        vtkGlyphRepresentationProxy,
        proxyUI.Glyph,
        proxyLinks.Glyph,
      ),
    },
    Views: {
      View3D: createDefaultView(vtkView, proxyUI.View3D),
      View2D: createDefaultView(vtk2DView, proxyUI.View2D),
      View2D_X: createDefaultView(vtk2DView, proxyUI.View2D, { axis: 0 }),
      View2D_Y: createDefaultView(vtk2DView, proxyUI.View2D, { axis: 1 }),
      View2D_Z: createDefaultView(vtk2DView, proxyUI.View2D, { axis: 2 }),
    },
  },
  representations: {
    View3D: proxyViewRepresentationMapping.View3D,
    View2D: proxyViewRepresentationMapping.View2D,
    View2D_X: {
      ...proxyViewRepresentationMapping.View2D,
      vtkImageData: { name: 'SliceX' },
    },
    View2D_Y: {
      ...proxyViewRepresentationMapping.View2D,
      vtkImageData: { name: 'SliceY' },
    },
    View2D_Z: {
      ...proxyViewRepresentationMapping.View2D,
      vtkImageData: { name: 'SliceZ' },
    },
  },
  filters: {
    vtkPolyData: [],
    vtkImageData: ['Contour'],
    vtkMolecule: [],
    Glyph: [],
  },
};
