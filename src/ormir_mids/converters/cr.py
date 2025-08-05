import os

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, slice_volume_3d, get_modality


def _is_cr(med_volume: MedicalVolume):
    """
    Check if the given MedicalVolume is a cr/dx dataset.
    Args:
        med_volume: The MedicalVolume to test.

    Returns:
        bool: True if the MedicalVolume is cr/dx dataset, False otherwise.
    """
    if 'CR' not in get_modality(med_volume) or 'DX' not in get_modality(med_volume):
        return False


class CrConverter(Converter):

    @classmethod
    def get_name(cls):
        return 'Plain_Radiography' 

    @classmethod
    def get_directory(cls):
        return os.path.join('rx')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_cr')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_cr(med_volume):
            return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, 1) # This will give an error, slices list is just 1?
        # add the important headerds here
        med_volume_out.omids_header['KVP'] = get_raw_tag_value(med_volume, '00180060')[0]
        med_volume_out.omids_header['ExposureTime'] = get_raw_tag_value(med_volume, '00181150')[0]
        med_volume_out.omids_header['X-RayTubeCurrent'] = get_raw_tag_value(med_volume, '00181151')[0]
        med_volume_out.omids_header['Exposure'] = get_raw_tag_value(med_volume, '00181152')[0]

        return med_volume_out
