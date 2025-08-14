import os

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, get_manufacturer


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
        if 'GE' not in get_manufacturer(med_volume):
            return False

        # check if magnitude
        try:
            image_type = get_raw_tag_value(med_volume, '0043102F')[0]
            if image_type[0] != 0:
                return False
        except:
            pass

        scanning_sequence = med_volume.omids_header['ScanningSequence']
        n_echo_times = len(med_volume.omids_header['EchoTime'])

        if scanning_sequence == 'SE' and n_echo_times > 1:
            return True

        return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        med_volume_out = group(med_volume, 'EchoTime')
        med_volume_out.omids_header['PulseSequenceType'] \
            = 'Multi-echo Spin Echo'
        med_volume_out.omids_header['RefocusingFlipAngle'] = 180.0
        return med_volume_out

