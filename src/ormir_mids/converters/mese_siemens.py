import os

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, get_manufacturer

class MeSeConverterSiemensMagnitude(Converter):

    @classmethod
    def get_name(cls):
        return 'MESE_Siemens_Magnitude'

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-anat')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_mese')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if 'SIEMENS' not in get_manufacturer(med_volume):
            return False

        # check if magnitude
        try:
            image_type = get_raw_tag_value(med_volume, '00089208')[0] # this is defined in newer versions
            print(image_type)
            if image_type[0] != 'M':
                return False
        except:
            pass
        if 'M' not in get_raw_tag_value(med_volume, '00080008'):
            return False


        scanning_sequence = get_raw_tag_value(med_volume, '00180020')[0]
        print(scanning_sequence)
        # echo_times = get_raw_tag_value(med_volume, 'EchoTime')
        n_echo_times = len(med_volume.omids_header['EchoTime'])

        if (scanning_sequence == 'SE' or scanning_sequence == 'SPIN') and n_echo_times > 1: #maybe scanning_sequence is Siemens-specific?
            return True

        return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        med_volume_out = group(med_volume, 'EchoTime')

        # rename flip angle. Maybe Siemens-specific again?
        med_volume_out.omids_header['RefocusingFlipAngle'] = med_volume_out.omids_header.pop('FlipAngle')
        med_volume_out.omids_header['PulseSequenceType'] = 'Multi-echo Spin Echo'

        return med_volume_out

