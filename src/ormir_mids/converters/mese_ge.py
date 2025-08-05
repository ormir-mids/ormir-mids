import math
import os

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, slice_volume_3d, get_manufacturer


def _is_mese_ge(med_volume: MedicalVolume):
    """
    Check if the given MedicalVolume is a MESE GE dataset.
    Args:
        med_volume: The MedicalVolume to test.

    Returns:
        bool: True if the MedicalVolume is a MESE GE dataset, False otherwise.
    """
    if 'GE' not in get_manufacturer(med_volume):
        return False
    scanning_sequence_list = med_volume.omids_header['ScanningSequence']
    echo_times_list = med_volume.omids_header['EchoTime']

    if isinstance(echo_times_list, list) and 'SE' in scanning_sequence_list:
        return True
    return False


def _test_ima_type(med_volume: MedicalVolume, ima_type: str):
    """
    Test if the given MedicalVolume is of the given type.
    Args:
        med_volume (MedicalVolume): The MedicalVolume to test.
        ima_type (str): The type to test, e.g. "MAGNITUDE", "PHASE"

    Returns:
        bool: True if the MedicalVolume is of the given type, False otherwise.
    """
    ima_type_list = get_raw_tag_value(med_volume, '00089208')
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
        dictionary: A dictionary containing lists of indices for magnitude, phase, and reco.
    """
    ima_index = {'magnitude': [],
                 'phase': [],
                 'reco': []
                 }

    ima_type_list = get_raw_tag_value(med_volume, '00089208')
    flat_ima_type = [x for xs in ima_type_list for x in xs]

    scanning_sequence_list = med_volume.omids_header['ScanningSequence']

    for i in range(len(flat_ima_type)):
        if (flat_ima_type[i] == 'MAGNITUDE' and scanning_sequence_list[i] == 'SE'):
            ima_index['magnitude'].append(i)
        elif (flat_ima_type[i] == 'PHASE' and scanning_sequence_list[i] == 'SE'):
            ima_index['phase'].append(i)
        elif scanning_sequence_list[i] == 'RM':
            ima_index['reco'].append(i)

    return ima_index


class MeSeConverterGEMagnitude(Converter):

    @classmethod
    def get_name(cls):
        return 'MESE_GE_Magnitude'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_mese')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_mese_ge(med_volume):
            return False

        return _test_ima_type(med_volume, 'MAGNITUDE')

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['magnitude'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Spin Echo'
        med_volume_out = group(med_volume_out, 'EchoTime')
        med_volume_out.omids_header['RefocusingFlipAngle'] = 180.0
        return med_volume_out


class MeSeConverterGEPhase(Converter):

    @classmethod
    def get_name(cls):
        return 'MESE_GE_Phase'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_mese_ph')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_mese_ge(med_volume):
            return False

        return _test_ima_type(med_volume, 'PHASE')

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['phase'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Spin Echo'
        med_volume_out = group(med_volume_out, 'EchoTime')
        med_volume_out.volume = (med_volume_out.volume - 2048) * math.pi / 2048 # convert to radians
        med_volume_out.omids_header['RefocusingFlipAngle'] = 180.0
        return med_volume_out


class MeSeConverterGEReconstructedMap(Converter):

    @classmethod
    def get_name(cls):
        return 'MESE_GE_ReconstructedT2'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-quant')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_t2')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if 'GE' not in get_manufacturer(med_volume):
            return False
        scanning_sequence_list = med_volume.omids_header['ScanningSequence']

        if 'RM' in scanning_sequence_list:
            return True
        return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['reco'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Spin Echo'
        return med_volume_out

