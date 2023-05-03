import vtkITKImageReader from 'vtk.js/Sources/IO/Misc/ITKImageReader';
// eslint-disable-next-line import/no-extraneous-dependencies
import { readImageArrayBuffer } from 'itk-wasm';

import ReaderFactory from './ReaderFactory';

vtkITKImageReader.setReadImageArrayBufferFromITK(readImageArrayBuffer);

ReaderFactory.registerReader({
  extension: 'nii',
  name: 'NII Reader',
  vtkReader: vtkITKImageReader,
  binary: true,
  fileNameMethod: 'setFileName',
});

ReaderFactory.registerReader({
  extension: 'nii.gz',
  name: 'NII.GZ Reader',
  vtkReader: vtkITKImageReader,
  binary: true,
  fileNameMethod: 'setFileName',
});

ReaderFactory.registerReader({
  extension: 'nrrd',
  name: 'NRRD Reader',
  vtkReader: vtkITKImageReader,
  binary: true,
  fileNameMethod: 'setFileName',
});

ReaderFactory.registerReader({
  extension: 'mgz',
  name: 'MGZ Reader',
  vtkReader: vtkITKImageReader,
  binary: true,
  fileNameMethod: 'setFileName',
});
