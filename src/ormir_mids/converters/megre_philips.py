import os
import numpy as np

from .PhilipsMR import PhilipsMRConverter
from ..converter_base.abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, slice_volume_3d


def get_raw_scanning_sequence(med_volume: MedicalVolume):
    return [v[0] for v in get_raw_tag_value(med_volume, '00180020', force_raw=True)]

def _is_megre_philips(med_volume: MedicalVolume):
    """
    Check if the given MedicalVolume is a MEGRE Philips dataset.
    Args:
        med_volume: The MedicalVolume to test.

    Returns:
        bool: True if the MedicalVolume is a MEGRE Philips dataset, False otherwise.
    """

    scanning_sequence_list = med_volume.omids_header['ScanningSequence']
    echo_times_list = med_volume.omids_header['EchoTime']
    echo_times_unique = set(echo_times_list)
    n_echo_times = sum(TE > 0. for TE in echo_times_unique)

    if ('GR' in scanning_sequence_list or 'GRADIENT' in scanning_sequence_list) and n_echo_times > 1:
        return True

    return False

def _get_ima_type(med_volume):
    try:
        # this is defined in the newer version of SIEMENS DICOMS and in Philips DICOMs
        flat_ima_type = get_raw_tag_value(med_volume, '00089208')
    except KeyError:
        ima_type_list = get_raw_tag_value(med_volume, '00080008')
        if isinstance(ima_type_list[0], list):
            flat_ima_type = ['/'.join(x) for x in ima_type_list]
        else:
            flat_ima_type = ima_type_list

    scanning_sequence_list = get_raw_scanning_sequence(med_volume)

    for i in range(len(flat_ima_type)):
        if 'MAGNITUDE' in flat_ima_type[i] or '/M/' in flat_ima_type[i]:
            flat_ima_type[i] = 0
        elif 'PHASE' in flat_ima_type[i] or '/P/' in flat_ima_type[i]:
            flat_ima_type[i] = 1
        elif 'REAL' in flat_ima_type[i] or '/R/' in flat_ima_type[i]:
            flat_ima_type[i] = 2
        elif 'IMAGINARY' in flat_ima_type[i] or '/I/' in flat_ima_type[i]:
            flat_ima_type[i] = 3
        # Account for derived images that also have M/P/R/I ima_type
        if scanning_sequence_list[i] == 'RM':
            flat_ima_type[i] = 4

    return flat_ima_type

def _test_ima_type(med_volume: MedicalVolume, ima_type: str):
    """
    Test if the given MedicalVolume is of the given type.
    Args:
        med_volume (MedicalVolume): The MedicalVolume to test.
        ima_type (int): The type to test, 0 = Magnitude, 1 = Phase, 2 = Real, 3 = Imaginary

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
    res_freq = get_raw_tag_value(med_volume, '00180084')[0]
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
                 'imaginary': [],
                 'reco': []
                 }

    flat_ima_type = _get_ima_type(med_volume)

    scanning_sequence_list = get_raw_scanning_sequence(med_volume)

    for i in range(len(flat_ima_type)):
        if flat_ima_type[i] == 0 and scanning_sequence_list[i] in ['GR', 'GRADIENT']:
            ima_index['magnitude'].append(i)
        elif flat_ima_type[i] == 1 and scanning_sequence_list[i] in ['GR', 'GRADIENT']:
            ima_index['phase'].append(i)
        elif flat_ima_type[i] == 2 and scanning_sequence_list[i] in ['GR', 'GRADIENT']:
            ima_index['real'].append(i)
        elif flat_ima_type[i] == 3 and scanning_sequence_list[i] in ['GR', 'GRADIENT']:
            ima_index['imaginary'].append(i)
        elif flat_ima_type[i] == 4:
            ima_index['reco'].append(i)

    return ima_index


class MeGreConverterPhilipsRoot(Converter):

    @classmethod
    def get_name(cls):
        return 'MEGRE_Philips_Root'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        return _is_megre_philips(med_volume)

MeGreConverterPhilipsRoot.set_parent(PhilipsMRConverter)

class MeGreConverterPhilipsMagnitude(Converter):

    @classmethod
    def get_name(cls):
        return 'MEGRE_Philips_Magnitude'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_suffix(cls):
        return '_MEGRE'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        return _test_ima_type(med_volume, 0)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['magnitude'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'
        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]

        # TO DO - incorporate code below into function
        echo_times_list = med_volume.omids_header['EchoTime']
        echo_times_nu = [echo_times_list[i] for i in indices['magnitude']]
        med_volume_out.omids_header['EchoTime'] = echo_times_nu
        med_volume_out = group(med_volume_out, 'EchoTime')

        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]
        med_volume_out.omids_header['WaterFatShift'] = _water_fat_shift_calc(med_volume)

        return med_volume_out


class MeGreConverterPhilipsPhase(Converter):

    @classmethod
    def get_name(cls):
        return 'MEGRE_Philips_Phase'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_suffix(cls):
        return '_part-phase_MEGRE'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        return _test_ima_type(med_volume, 1)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['phase'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'

        # TO DO - incorporate code below into function
        echo_times_list = med_volume.omids_header['EchoTime']
        echo_times_nu = [echo_times_list[i] for i in indices['phase']]
        med_volume_out.omids_header['EchoTime'] = echo_times_nu
        med_volume_out = group(med_volume_out, 'EchoTime')

        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]
        med_volume_out.omids_header['WaterFatShift'] = _water_fat_shift_calc(med_volume)

        med_volume_out.volume = np.where(med_volume_out.volume != 0,
                                         (med_volume_out.volume - 2048.) * np.pi / 2048.,
                                         med_volume_out.volume).astype(np.float32)

        return med_volume_out


class MeGreConverterPhilipsReal(Converter):

    @classmethod
    def get_name(cls):
        return 'MEGRE_Philips_Real'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_suffix(cls):
        return '_part-real_MEGRE'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        return _test_ima_type(med_volume, 2)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['real'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'

        # TO DO - incorporate code below into function
        echo_times_list = med_volume.omids_header['EchoTime']
        echo_times_nu = [echo_times_list[i] for i in indices['real']]
        med_volume_out.omids_header['EchoTime'] = echo_times_nu
        med_volume_out = group(med_volume_out, 'EchoTime')

        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]
        med_volume_out.omids_header['WaterFatShift'] = _water_fat_shift_calc(med_volume)

        return med_volume_out


class MeGreConverterPhilipsImaginary(Converter):

    @classmethod
    def get_name(cls):
        return 'MEGRE_Philips_Imaginary'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_suffix(cls):
        return '_part-imag_MEGRE'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        return _test_ima_type(med_volume, 3)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['imaginary'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'

        # TO DO - incorporate code below into function
        echo_times_list = med_volume.omids_header['EchoTime']
        echo_times_nu = [echo_times_list[i] for i in indices['imaginary']]
        med_volume_out.omids_header['EchoTime'] = echo_times_nu
        med_volume_out = group(med_volume_out, 'EchoTime')

        med_volume_out.omids_header['MagneticFieldStrength'] = get_raw_tag_value(med_volume, '00180087')[0]
        med_volume_out.omids_header['WaterFatShift'] = _water_fat_shift_calc(med_volume)

        return med_volume_out


class MeGreConverterPhilipsReconstructedMap(Converter):
    # TO DO - new classes for FF, water, fat etc.

    @classmethod
    def get_name(cls):
        return 'MEGRE_Philips_Reconstructed'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-quant')

    @classmethod
    def get_suffix(cls):
        return '_MEGRE_RECO'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        scanning_sequence_list = get_raw_scanning_sequence(med_volume)

        if 'RM' in scanning_sequence_list and ('GRADIENT' in scanning_sequence_list or 'GR' in scanning_sequence_list):
            return True
        return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['reco'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'
        return med_volume_out

MeGreConverterPhilipsMagnitude.set_parent(MeGreConverterPhilipsRoot)
MeGreConverterPhilipsPhase.set_parent(MeGreConverterPhilipsRoot)
MeGreConverterPhilipsReal.set_parent(MeGreConverterPhilipsRoot)
MeGreConverterPhilipsImaginary.set_parent(MeGreConverterPhilipsRoot)
MeGreConverterPhilipsReconstructedMap.set_parent(PhilipsMRConverter)