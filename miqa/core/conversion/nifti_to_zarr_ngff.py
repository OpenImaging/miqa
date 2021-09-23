__all__ = ['nifti_to_zarr_ngff']

from pathlib import Path
from typing import Union

import itk
import spatial_image_multiscale
import spatial_image_ngff
import zarr


def nifti_to_zarr_ngff(nifti_file: Union[str, Path]) -> Path:
    """Convert the nifti file on disk to a Zarr NGFF store.

    The Zarr store will have the same path with '.zarr' appended.

    If the store already exists, it will not be re-created.
    """
    store_path = Path(str(nifti_file) + '.zarr')
    if store_path.exists():
        return store_path
    image = itk.imread(str(nifti_file))
    da = itk.xarray_from_image(image)
    da.name = 'image'

    scale_factors = [2, 2, 2, 2]
    multiscale = spatial_image_multiscale.to_multiscale(da, scale_factors)

    store_path = Path(str(nifti_file) + '.zarr')
    store = zarr.NestedDirectoryStore(str(nifti_file) + '.zarr')
    spatial_image_ngff.imwrite(multiscale, store)

    return store_path
