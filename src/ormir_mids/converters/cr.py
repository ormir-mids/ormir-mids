import os

from ..converter_base.abstract_converter import Converter, RootConverter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, slice_volume_3d, get_modality


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
    def get_suffix(cls):
        return '_cr'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_cr(med_volume):
            return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):

        # add the important headerds here
        med_volume.omids_header['KVP'] = get_raw_tag_value(med_volume, '00180060')[0]
        med_volume.omids_header['ExposureTime'] = get_raw_tag_value(med_volume, '00181150')[0]
        med_volume.omids_header['X-RayTubeCurrent'] = get_raw_tag_value(med_volume, '00181151')[0]
        med_volume.omids_header['Exposure'] = get_raw_tag_value(med_volume, '00181152')[0]

        return med_volume

CrConverter.set_parent(RootConverter)