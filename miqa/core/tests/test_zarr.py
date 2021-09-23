import os
from pathlib import Path
import shutil

from miqa.core.conversion.nifti_to_zarr_ngff import nifti_to_zarr_ngff


def test_convert_to_zarr():
    script_dir = Path(__file__).resolve().parent
    samples_dir = script_dir / '..' / '..' / '..' / 'samples'
    samples = [
        samples_dir
        / Path(
            'datasnap-2019-01-23/fs/storage/XNAT/archive/ohsu_incoming/arc001/D-99999-P-9-2081220/RESOURCES/nifti/2_ncanda-mprage-v1/image.nii.gz'  # noqa: E501
        ),
        samples_dir
        / Path(
            'datasnap-2019-01-23/fs/storage/XNAT/archive/ohsu_incoming/arc001/D-99999-P-9-2081220/RESOURCES/nifti/2_ncanda-mprage-v1/image.nii.gz'  # noqa: E501
        ),
    ]

    sample = samples[0]

    for sample in samples:
        result = str(sample) + '.zarr'
        if os.path.exists(result):
            shutil.rmtree(result)
        result_path = nifti_to_zarr_ngff(sample)
        assert str(result_path) == result
        assert os.path.exists(result)
