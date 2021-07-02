import vtkITKImageReader from 'vtk.js/Sources/IO/Misc/ITKImageReader';
import readImageArrayBuffer from 'itk/readImageArrayBuffer';

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
