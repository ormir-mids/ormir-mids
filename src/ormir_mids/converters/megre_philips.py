import os

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, slice_volume_3d, get_manufacturer


def _is_megre_philips(med_volume: MedicalVolume):
    """
    Check if the given MedicalVolume is a MEGRE Philips dataset.
    Args:
        med_volume: The MedicalVolume to test.

    Returns:
        bool: True if the MedicalVolume is a MEGRE Philips dataset, False otherwise.
    """
    if 'PHILIPS'.lower() not in get_manufacturer(med_volume).lower():
        return False

    scanning_sequence_list = med_volume.omids_header['ScanningSequence']
    echo_times_list = med_volume.omids_header['EchoTime']
    echo_times_unique = set(echo_times_list)
    n_echo_times = sum(TE > 0. for TE in echo_times_unique)

    if n_echo_times > 1 and 'GR' in scanning_sequence_list:
        return True
    return False


def _test_ima_type(med_volume: MedicalVolume, ima_type: int):
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

    ima_type_list = get_raw_tag_value(med_volume, '00089208')  # DC-3T: Or 00080008 for Classic DICOM?
    flat_ima_type = [x for xs in ima_type_list for x in xs]

    scanning_sequence_list = med_volume.omids_header['ScanningSequence']
    # DCam - The below code causes errors. Remove?
    #if ~isinstance(scanning_sequence_list, list):
        #scanning_sequence_list = [scanning_sequence_list] * len(flat_ima_type)

    for i in range(len(flat_ima_type)):
        if flat_ima_type[i] == 'MAGNITUDE' and scanning_sequence_list[i] == 'GR':
            ima_index['magnitude'].append(i)
        elif flat_ima_type[i] == 'PHASE' and scanning_sequence_list[i] == 'GR':
            ima_index['phase'].append(i)
        elif flat_ima_type[i] == 'REAL' and scanning_sequence_list[i] == 'GR':
            ima_index['real'].append(i)
        elif flat_ima_type[i] == "IMAGINARY" and scanning_sequence_list[i] == 'GR':
            ima_index['imaginary'].append(i)
        elif scanning_sequence_list[i] == 'RM':
            ima_index['reco'].append(i)

    return ima_index


class MeGreConverterPhilipsMagnitude(Converter):

    @classmethod
    def get_name(cls):
        return 'MEGRE_Philips_Magnitude'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_megre_philips(med_volume):
            return False

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
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre_ph')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_megre_philips(med_volume):
            return False

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

        med_volume_out.volume = (med_volume_out.volume - 2048).astype(np.float32) * np.pi / 2048

        return med_volume_out


class MeGreConverterPhilipsReal(Converter):

    @classmethod
    def get_name(cls):
        return 'MEGRE_Philips_Real'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre_real')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_megre_philips(med_volume):
            return False

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
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre_imag')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if not _is_megre_philips(med_volume):
            return False

        return _test_ima_type(med_volume, 3)

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['imaginary'])
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Gradient Echo'

        # TO DO - incorporate code below into function
        echo_times_list = med_volume.omids_header['EchoTime']
        echo_times_nu = [echo_times_list[i] for i in indices['magnitude']]
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
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_megre_reco')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if 'PHILIPS'.lower() not in get_manufacturer(med_volume).lower():
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
