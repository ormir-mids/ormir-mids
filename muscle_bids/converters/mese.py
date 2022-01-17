import os

from .abstract_converter import Converter
from ..dosma_io import MedicalVolume
from ..utils.headers import get_raw_tag_value, group


class MeseConverter(Converter):

    @staticmethod
    def get_name():
        return 'MESE'

    @staticmethod
    def get_directory():
        return 'anat'

    @staticmethod
    def get_file_name(subject_id: str):
        return os.path.join(f'{subject_id}_mese')

    @staticmethod
    def is_dataset_compatible(med_volume: MedicalVolume):
        scanning_sequence = get_raw_tag_value(med_volume, '00180020')[0]
        echo_train_length = get_raw_tag_value(med_volume, '00180091')[0]
        # echo_times = get_raw_tag_value(med_volume, 'EchoTime')

        if scanning_sequence == 'SE' and echo_train_length > 1: #maybe scanning_sequence is Siemens-specific?
            return True

        return False

    @staticmethod
    def convert_dataset(med_volume: MedicalVolume):
        med_volume_out = group(med_volume, 'EchoTime')

        # rename flip angle. Maybe Siemens-specific again?
        med_volume_out.bids_header['RefocusingFlipAngle'] = med_volume_out.bids_header.pop('FlipAngle')

        return med_volume_out

