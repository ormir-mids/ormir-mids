import os

import numpy as np

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, slice_volume_3d, get_manufacturer


# TODO: DC-3T - Incorporate changes from offline megre_siemens converter

def _is_megre_siemens(med_volume: MedicalVolume):
    """
    Check if the given MedicalVolume is a MEGRE Siemens dataset.
    Args:
        med_volume: The MedicalVolume to test.

    Returns:
        bool: True if the MedicalVolume is a MEGRE Siemens dataset, False otherwise.
    """
    if 'Siemens'.lower() not in get_manufacturer(med_volume).lower():
        return False

    scanning_sequence_list = med_volume.omids_header['ScanningSequence']

    if 'GR' in scanning_sequence_list or 'GRADIENT' in scanning_sequence_list:
        return True
    return False

def _get_ima_type(med_volume):
    try:
        # this is defined in the newer version of SIEMENS DICOMS and in Philips DICOMs
        flat_ima_type = get_raw_tag_value(med_volume, '00089208')
    except KeyError:
        ima_type_list = get_raw_tag_value(med_volume, '00080008')
        if isinstance(ima_type_list[0], str):
            flat_ima_type = ['/'.join(ima_type_list)]
        else:
            flat_ima_type = ima_type_list


    for i in range(len(flat_ima_type)):
        if flat_ima_type[i].startswith('M') or '/M' in flat_ima_type[i]:
            flat_ima_type[i] = 0
        elif flat_ima_type[i].startswith('P') or '/P' in flat_ima_type[i]:
            flat_ima_type[i] = 1
        elif flat_ima_type[i].startswith('R') or '/R' in flat_ima_type[i]:
            flat_ima_type[i] = 2
        elif flat_ima_type[i].startswith('I') or '/I' in flat_ima_type[i]:
            flat_ima_type[i] = 3

    return flat_ima_type

def _test_ima_type(med_volume: MedicalVolume, ima_type: int):
    """
    Test if the given MedicalVolume is of the given type.
    Args:
        med_volume (MedicalVolume): The MedicalVolume to test.
        ima_type (int): The type to test, 0 = Magnitude, 1 = Phase, 2 = Real, 3 = Imaginary."

    Returns:
        bool: True if the MedicalVolume is of the given type, False otherwise.
    """
    flat_ima_type = _get_ima_type(med_volume)

    if ima_type in flat_ima_type:
        return True
    return False


def _water_fat_shift_calc(med_volume: MedicalVolume):
    """
    Calculate water-fat shift in pixels from image header.
    Args:
        med_volume (MedicalVolume): The MedicalVolume to test.

    Returns:
        float: the value of the water-fat shift in pixels.
    """
    bw_per_pix = get_raw_tag_value(med_volume, '00180095')[0]
    res_freq = get_raw_tag_value(med_volume, '00180084', '00189098')[0]
    water_fat_diff_ppm = 3.35
    water_fat_shift_hz = water_fat_diff_ppm * res_freq
    water_fat_shift_px = water_fat_shift_hz / bw_per_pix

    return water_fat_shift_px


def _get_image_indices(med_volume: MedicalVolume):
    """
    Get the indices for magnitude, phase, and reco for the given MedicalVolume.
    Args:
        med_volume (MedicalVolume): The MedicalVolume to test.

    Returns:
        dictionary: A dictionary containing lists of indices for magnitude, phase, real, imaginary, and reco.
    """
    ima_index = {'magnitude': [],
                 'phase': [],
                 'real': [],
                 'imaginary': []
                 }

    flat_ima_type = _get_ima_type(med_volume)

    for i in range(len(flat_ima_type)):
        if flat_ima_type[i] == 0:
            ima_index['magnitude'].append(i)
        elif flat_ima_type[i] == 1:
            ima_index['phase'].append(i)
        elif flat_ima_type[i] == 2:
            ima_index['real'].append(i)
        elif flat_ima_type[i] == 3:
            ima_index['imaginary'].append(i)

    return ima_index

def _get_echo_times(echo_times_list, indices, ima_type: str):
    """
    Get the echo times for the given ima_type.
    Args:
        echo_times_list: list of echo times as taken from the header
        indices: list of indices for the ima_type
        ima_type: 'magnitude', 'phase', 'real', or 'imaginary'

    Returns:

    """
    try:
        echo_times_nu = [echo_times_list[i] for i in indices[ima_type]]
    except TypeError:
        # echo time is not a vector
        echo_times_nu = [echo_times_list] * len(indices[ima_type])
    return echo_times_nu

class MeGreConverterSiemensMagnitude(Converter):

    @classmethod
    def is_multiseries(cls):
        return True

    @classmethod
    def get_name(cls):
        return 'MEGRE_Siemens_Magnitude'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_megre_siemens(med_volume):
            return False

        return _test_ima_type(med_volume, 0)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)

        image_comment = get_raw_tag_value(med_volume, '00204000')
        if isinstance(image_comment, list):
            image_comment = image_comment[0]
        if image_comment.startswith('TE [ms]:'):
            echo_time = float(image_comment[len('TE [ms]:'):])
            med_volume.omids_header['EchoTime'] = echo_time
        med_volume_out = slice_volume_3d(med_volume, indices['magnitude'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'
        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]

        # TO DO - incorporate code below into function
        echo_times_list = med_volume.omids_header['EchoTime']
        echo_times_nu = _get_echo_times(echo_times_list, indices, 'magnitude')
        med_volume_out.omids_header['EchoTime'] = echo_times_nu
        med_volume_out = group(med_volume_out, 'EchoTime')

        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]
        med_volume_out.omids_header['WaterFatShift'] = _water_fat_shift_calc(med_volume)

        if 'ImageTypePhilips' in med_volume.omids_header:
            med_volume_out.omids_header['ImageType'] = med_volume.omids_header['ImageTypePhilips']
            del med_volume_out.omids_header['ImageTypePhilips']
            del med_volume_out.omids_header['ImageTypeSiemens']
        else:
            med_volume_out.omids_header['ImageType'] = med_volume.omids_header['ImageTypeSiemens']
            del med_volume_out.omids_header['ImageTypeSiemens']

        return med_volume_out


class MeGreConverterSiemensPhase(Converter):

    @classmethod
    def is_multiseries(cls):
        return True

    @classmethod
    def get_name(cls):
        return 'MEGRE_Siemens_Phase'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre_ph')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_megre_siemens(med_volume):
            return False

        return _test_ima_type(med_volume, 1)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['phase'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'

        # TO DO - incorporate code below into function
        echo_times_list = med_volume.omids_header['EchoTime']
        echo_times_nu = _get_echo_times(echo_times_list, indices, 'phase')
        med_volume_out.omids_header['EchoTime'] = echo_times_nu
        med_volume_out = group(med_volume_out, 'EchoTime')

        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]
        med_volume_out.omids_header['WaterFatShift'] = _water_fat_shift_calc(med_volume)

        med_volume_out.volume = (med_volume_out.volume - 2048).astype(np.float32) * np.pi / 2048
        if 'ImageTypePhilips' in med_volume.omids_header:
            med_volume_out.omids_header['ImageType'] = med_volume.omids_header['ImageTypePhilips']
            del med_volume_out.omids_header['ImageTypePhilips']
            del med_volume_out.omids_header['ImageTypeSiemens']
        else:
            med_volume_out.omids_header['ImageType'] = med_volume.omids_header['ImageTypeSiemens']

        return med_volume_out



class MeGreConverterSiemensReal(Converter):

    @classmethod
    def is_multiseries(cls):
        return True

    @classmethod
    def get_name(cls):
        return 'MEGRE_Siemens_Real'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre_real')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_megre_siemens(med_volume):
            return False

        return _test_ima_type(med_volume, 2)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['real'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'

        # TO DO - incorporate code below into function
        echo_times_list = med_volume.omids_header['EchoTime']
        echo_times_nu = _get_echo_times(echo_times_list, indices, 'real')
        med_volume_out.omids_header['EchoTime'] = echo_times_nu
        med_volume_out = group(med_volume_out, 'EchoTime')

        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]
        med_volume_out.omids_header['WaterFatShift'] = _water_fat_shift_calc(med_volume)
        if 'ImageTypePhilips' in med_volume.omids_header:
            med_volume_out.omids_header['ImageType'] = med_volume.omids_header['ImageTypePhilips']
            del med_volume_out.omids_header['ImageTypePhilips']
            del med_volume_out.omids_header['ImageTypeSiemens']
        else:
            med_volume_out.omids_header['ImageType'] = med_volume.omids_header['ImageTypeSiemens']

        return med_volume_out


class MeGreConverterSiemensImaginary(Converter):

    @classmethod
    def is_multiseries(cls):
        return True

    @classmethod
    def get_name(cls):
        return 'MEGRE_Siemens_Imaginary'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre_imag')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_megre_siemens(med_volume):
            return False

        return _test_ima_type(med_volume, 3)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['imaginary'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'

        # TO DO - incorporate code below into function
        echo_times_list = med_volume.omids_header['EchoTime']
        echo_times_nu = _get_echo_times(echo_times_list, indices, 'imaginary')
        med_volume_out.omids_header['EchoTime'] = echo_times_nu
        med_volume_out = group(med_volume_out, 'EchoTime')

        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]
        med_volume_out.omids_header['WaterFatShift'] = _water_fat_shift_calc(med_volume)
        if 'ImageTypePhilips' in med_volume.omids_header:
            med_volume_out.omids_header['ImageType'] = med_volume.omids_header['ImageTypePhilips']
            del med_volume_out.omids_header['ImageTypePhilips']
            del med_volume_out.omids_header['ImageTypeSiemens']
        else:
            med_volume_out.omids_header['ImageType'] = med_volume.omids_header['ImageTypeSiemens']

        return med_volume_out


class MeGreConverterSiemensReconstructedMap(Converter):
    # TO DO - new classes for FF, water, fat etc.

    @classmethod
    def get_name(cls):
        return 'MEGRE_Siemens_Reconstructed'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-quant')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre_reco')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if 'Siemens'.lower() not in get_manufacturer(med_volume).lower():
            return False
        scanning_sequence_list = med_volume.omids_header['ScanningSequence']

        if 'RM' in scanning_sequence_list:
            return True
        return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['reco'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'
        return med_volume_out
