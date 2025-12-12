import math
import os

from .PhilipsMR import PhilipsMRConverter
from ..converter_base.abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, slice_volume_3d, get_manufacturer


def get_raw_scanning_sequence(med_volume: MedicalVolume):
    return [v[0] for v in get_raw_tag_value(med_volume, '00180020', force_raw=True)]

def _is_mese_philips(med_volume: MedicalVolume):
    """
    Check if the given MedicalVolume is a MESE Philips dataset.
    Parameters:
        med_volume: The MedicalVolume to test.

    Returns:
        bool: True if the MedicalVolume is a MESE Philips dataset, False otherwise.
    """
    scanning_sequence_list = get_raw_scanning_sequence(med_volume)
    echo_times_list = med_volume.omids_header['EchoTime']

    if (isinstance(echo_times_list, list) and
            ('SE' in scanning_sequence_list or 'SPIN' in scanning_sequence_list)):
        return True
    return False


def _test_ima_type(med_volume: MedicalVolume, ima_type: str):
    """
    Test if the given MedicalVolume is of the given type.
    Parameters:
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
    Parameters:
        med_volume (MedicalVolume): The MedicalVolume to test.

    Returns:
        dictionary: A dictionary containing lists of indices for magnitude, phase, and reco.
    """
    ima_index = {'magnitude': [],
                 'phase': [],
                 'reco': []
                 }

    ima_type_list = get_raw_tag_value(med_volume, '00089208')
    flat_ima_type = [x[0] for x in ima_type_list]

    scanning_sequence_list = get_raw_scanning_sequence(med_volume)

    for i in range(len(flat_ima_type)):
        if flat_ima_type[i] == 'MAGNITUDE' and scanning_sequence_list[i] in ['SE', 'SPIN']:
            ima_index['magnitude'].append(i)
        elif flat_ima_type[i] == 'PHASE' and scanning_sequence_list[i] in ['SE', 'SPIN']:
            ima_index['phase'].append(i)
        elif scanning_sequence_list[i] == 'RM':
            ima_index['reco'].append(i)

    return ima_index


class MeSeConverterPhilipsRoot(Converter):
    @classmethod
    def get_name(cls):
        return 'MESE_Philips_Root'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        return _is_mese_philips(med_volume)


MeSeConverterPhilipsRoot.set_parent(PhilipsMRConverter)

class MeSeConverterPhilipsMagnitude(Converter):

    @classmethod
    def get_name(cls):
        return 'MESE_Philips_Magnitude'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_suffix(cls):
        return '_MESE'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        return _test_ima_type(med_volume, 'MAGNITUDE')

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['magnitude'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Spin Echo'
        med_volume_out = group(med_volume_out, 'EchoTime')
        med_volume_out.omids_header['RefocusingFlipAngle'] = 180.0
        return med_volume_out


class MeSeConverterPhilipsPhase(Converter):

    @classmethod
    def get_name(cls):
        return 'MESE_Philips_Phase'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_suffix(cls):
        return '_part-phase_MESE'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
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


class MeSeConverterPhilipsReconstructedMap(Converter):

    @classmethod
    def get_name(cls):
        return 'MESE_Philips_ReconstructedT2'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-quant')

    @classmethod
    def get_suffix(cls):
        return '_T2'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        scanning_sequence_list = get_raw_scanning_sequence(med_volume)

        if 'RM' in scanning_sequence_list:
            return True
        return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['reco'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Spin Echo'
        return med_volume_out

MeSeConverterPhilipsMagnitude.set_parent(MeSeConverterPhilipsRoot)
MeSeConverterPhilipsPhase.set_parent(MeSeConverterPhilipsRoot)
MeSeConverterPhilipsReconstructedMap.set_parent(PhilipsMRConverter)
