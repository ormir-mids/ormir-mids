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
    if 'CT' not in get_modality(med_volume):
        return False
    else:
        return True


def _test_ima_type(med_volume: MedicalVolume, ima_type: int):
    """
    Test if the given MedicalVolume is of the given type.
    Args:
        med_volume (MedicalVolume): The MedicalVolume to test.
        ima_type (int): The type to test (numeric value)

    Returns:
        bool: True if the MedicalVolume is of the given type, False otherwise.
    """
    ima_type_list = get_raw_tag_value(med_volume, '00080008')
    # Flatten the list if it's nested, don't split strings into characters
    if isinstance(ima_type_list[0], list):
        flat_ima_type = [item for sublist in ima_type_list for item in sublist]
    else:
        flat_ima_type = ima_type_list

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
                 'pcct': [],
                 'hrpqct': []
                 }

    ima_type_list = get_raw_tag_value(med_volume, '00080008')
    # Flatten if nested
    if isinstance(ima_type_list[0], list):
        flat_ima_type = [item for sublist in ima_type_list for item in sublist]
    else:
        flat_ima_type = ima_type_list

    for i in range(len(flat_ima_type)):
        if flat_ima_type[i] == 6:
            ima_index['pcct'].append(i)
        else:
            _manufacturer = get_raw_tag_value(med_volume, '00080070')[0]
            if 'SCANCO' in str(_manufacturer).upper():
                ima_index['hrpqct'].append(i)
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


class ScancoConverter(Converter):
    """
    Converter for Scanco HR-pQCT datasets.
    """

    @classmethod
    def get_name(cls):
        return "HRpQCT"

    @classmethod
    def get_directory(cls):
        return "ct-hrpqct"

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f"{subject_id}_hrpqct")

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_ct(med_volume) and 'SCANCO' not in str(get_raw_tag_value(med_volume, '00080070')[0]).upper():
            return False
        return _test_ima_type(med_volume, "ORIGINAL")

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):

        indices = _get_image_indices(med_volume)
        # med_volume = slice_volume_3d(med_volume, indices["hrpqct"])

        # Standard DICOM tags
        med_volume.omids_header["Modality"] = get_modality(med_volume)
        med_volume.omids_header["XRayEnergy"] = get_raw_tag_value(med_volume, "00180060")[0]  # U peak (kV)
        med_volume.omids_header["XRayExposureTime"] = get_raw_tag_value(med_volume, "00181150")[0]  # ms
        med_volume.omids_header["XRayExposure"] = get_raw_tag_value(med_volume, "00181153")[0]  # μAs
        med_volume.omids_header["ConvolutionKernel"] = get_raw_tag_value(med_volume, "00181210")[0]

        # SCANCO rescale tags --> needed to calibrate image to BMD
        med_volume.omids_header["RescaleIntercept"] = get_raw_tag_value(med_volume, "00281052")[0]
        med_volume.omids_header["RescaleSlope"] = get_raw_tag_value(med_volume, "00281053")[0]
        med_volume.omids_header["ScancoMuScaling"] = get_raw_tag_value(med_volume, "00291000")[0]  # (0029,1000) scaling info
        med_volume.omids_header["ScancoDensitySlope"] = get_raw_tag_value(med_volume, "00291004")[0]  # (0029,1004) density slope
        med_volume.omids_header["ScancoDensityIntercept"] = get_raw_tag_value(med_volume, "00291005")[0]  # (0029,1005) density intercept
        med_volume.omids_header["ScancoMuWater"] = get_raw_tag_value(med_volume, "00291006")[0]  # (0029,1006) density factor

        return med_volume
