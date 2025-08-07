import os

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, slice_volume_3d, get_manufacturer


def _is_dess_ge(med_volume: MedicalVolume):
    """
    Check if the given MedicalVolume is a DESS (MENSA) GE dataset.
    Parameters:
        med_volume: The MedicalVolume to test.

    Returns:
        bool: True if the MedicalVolume is a DESS GE dataset, False otherwise.
    """
    if 'GE' not in get_manufacturer(med_volume):
        return False

    pulse_sequence_name = get_raw_tag_value(med_volume, '0019109C')[0]  # sequence name mensa*

    if "mensa" in pulse_sequence_name:
        return True

    return False


def _get_image_indices(med_volume: MedicalVolume):
    """
    Get the indices for FID, echo, and combined for the given MedicalVolume.
    Args:
        med_volume (MedicalVolume): The MedicalVolume to test.

    Returns:
        dictionary: A dictionary containing lists of indices for FID, echo,
        and combined.
    """
    ima_index = {'fid': [],
                 'echo': [],
                 'combined': []
                 }

    echo_times_list = med_volume.omids_header['EchoTime']  # DC-3T: Or 00080008 for Classic DICOM?
    echo_times_list = echo_times_list if isinstance(echo_times_list, list) \
        else [echo_times_list]
    if len(echo_times_list) > 1:
        n_echo_times = list(set(echo_times_list))
        if len(n_echo_times) == 2:
            for i in range(len(echo_times_list)):
                if echo_times_list[i] == min(n_echo_times):
                    ima_index['fid'].append(i)
                elif echo_times_list[i] == max(n_echo_times):
                    ima_index['echo'].append(i)
    else:
        ima_index['combined'].append(0)

    return ima_index


class DESSConverterGECombined(Converter):

    @classmethod
    def get_name(cls):
        return 'DESS_GE_Combined'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_dess')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        n_echo_times = get_raw_tag_value(med_volume, '0019107E')[0]
        if n_echo_times != 1:
            return False

        if not _is_dess_ge(med_volume):
            return False

        return True

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['combined'])

        med_volume_out.omids_header['PulseSequenceType'] = 'DESS'

        return med_volume_out


class DESSConverterGEFid(Converter):

    @classmethod
    def get_name(cls):
        return 'DESS_GE_FID'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_dess-fid')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        n_echo_times = get_raw_tag_value(med_volume, '0019107E')[0]
        if n_echo_times != 2:
            return False

        if not _is_dess_ge(med_volume):
            return False

        return True

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['fid'])

        med_volume_out.omids_header['PulseSequenceType'] = 'DESS'

        return med_volume_out


class DESSConverterGEEcho(Converter):

    @classmethod
    def get_name(cls):
        return 'DESS_GE_Echo'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
            return os.path.join(f'{subject_id}_dess-echo')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        n_echo_times = get_raw_tag_value(med_volume, '0019107E')[0]
        if n_echo_times != 2:
            return False

        if not _is_dess_ge(med_volume):
            return False

        return True

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        indices = _get_image_indices(med_volume)
        med_volume_out = slice_volume_3d(med_volume, indices['echo'])

        med_volume_out.omids_header['PulseSequenceType'] = 'DESS'

        return med_volume_out

