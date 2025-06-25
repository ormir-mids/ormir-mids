import os

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, slice_volume_3d, get_modality


def _is_ct(med_volume: MedicalVolume):
    """
    Check if the given MedicalVolume is a CT dataset.
    Args:
        med_volume: The MedicalVolume to test.

    Returns:
        bool: True if the MedicalVolume is a CT dataset, False otherwise.
    """
    #
    if 'CT' not in get_modality(med_volume):
        return False


def _test_ima_type(med_volume: MedicalVolume, ima_type: int):
    """
    Test if the given MedicalVolume is of the given type.
    Args:
        med_volume (MedicalVolume): The MedicalVolume to test.
        ima_type (str): The type to test, e.g. "COUNT"

    Returns:
        bool: True if the MedicalVolume is of the given type, False otherwise.
    """
    ima_type_list = get_raw_tag_value(med_volume, '00080008')
    flat_ima_type = [x for xs in ima_type_list for x in xs]

    if ima_type in flat_ima_type:
        return True
    return False


def _get_image_indices(med_volume: MedicalVolume):
    """
    Get the indices for magnitude, phase, and reco for the given MedicalVolume.
    Args:
        med_volume (MedicalVolume): The MedicalVolume to test.

    Returns:
        dictionary: A dictionary containing lists of indices for conventional and/or photon-counting CT.
    """
    ima_index = {'ct': [],
                 'pcct': []
                 }

    ima_type_list = get_raw_tag_value(med_volume, '00080008')
    flat_ima_type = [x for xs in ima_type_list for x in xs]

    for i in range(len(flat_ima_type)):
        if flat_ima_type[i] == 6:
            ima_index['pcct'].append(i)
        else:
            ima_index['ct'].append(i)

    return ima_index


class CTConverter(Converter):

    @classmethod
    def get_name(cls):
        return 'Conventional_CT'

    @classmethod
    def get_directory(cls):
        return 'ct-edi'

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_ct')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_ct(med_volume):
            return False

        return _test_ima_type(med_volume, 0)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['ct'])

        med_volume_out.omids_header['XRayEnergy'] = get_raw_tag_value(med_volume, '00180060')[0]
        med_volume_out.omids_header['XRayExposure'] = get_raw_tag_value(med_volume, '00181152')[0]

        return med_volume_out


class PCCTConverter(Converter):

    @classmethod
    def get_name(cls):
        return 'Photon-Counting_CT'

    @classmethod
    def get_directory(cls):
        return 'ct-pc'

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_pcct')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_ct(med_volume):
            return False

        return _test_ima_type(med_volume, 1)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['pcct'])

        med_volume_out.omids_header['XRayEnergy'] = get_raw_tag_value(med_volume, '00180060')[0]
        med_volume_out.omids_header['XRayExposure'] = get_raw_tag_value(med_volume, '00181152')[0]

        return med_volume_out
