__all__ = ['nifti_to_zarr_ngff', 'convert_to_store_path']

from pathlib import Path

from celery import shared_task


def convert_to_store_path(nifti_file: str) -> Path:
    """Provide the Zarr store Path for a Nifti path."""
    store_path = Path(nifti_file + '.zarr')
    return store_path


@shared_task
def nifti_to_zarr_ngff(nifti_file: str) -> str:
    """Convert the nifti file on disk to a Zarr NGFF store.

    The Zarr store will have the same path with '.zarr' appended.

    If the store already exists, it will not be re-created.
    """
    import itk
    import spatial_image_multiscale
    import spatial_image_ngff
    import zarr

    store_path = convert_to_store_path(nifti_file)
    if store_path.exists():
        return str(store_path)
    image = itk.imread(str(nifti_file))
    da = itk.xarray_from_image(image)
    da.name = 'image'

    scale_factors = [2, 2, 2, 2]
    multiscale = spatial_image_multiscale.to_multiscale(da, scale_factors)

    store_path = Path(str(nifti_file) + '.zarr')
    store = zarr.NestedDirectoryStore(str(nifti_file) + '.zarr')
    spatial_image_ngff.imwrite(multiscale, store)

    # celery tasks must return a serializable type; using string here
    return str(store_path)
