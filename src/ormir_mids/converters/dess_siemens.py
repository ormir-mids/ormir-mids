import os

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, get_manufacturer


class DESSConverterSiemensMagnitude(Converter):

    @classmethod
    def get_name(cls):
        return 'DESS_Siemens_Magnitude'

    @classmethod
    def get_directory(cls):
        return 'mr-anat'

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_DESS')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if 'SIEMENS' not in get_manufacturer(med_volume).upper():
            return False

        # check if magnitude
        # if 'M' not in get_raw_tag_value(med_volume, '00080008'):
        #     return False

        try:
            scanning_sequence = get_raw_tag_value(med_volume, '00180024')[0] #sequence name *de3d
        except KeyError:
            scanning_sequence = get_raw_tag_value(med_volume, '00189005')[0] #sequence name in enhanced dicom *de3d
        # echo_train_length = get_raw_tag_value(med_volume, '00180091')[0]
        # echo_times = get_raw_tag_value(med_volume, 'EchoTime')  # Two echo times reported?

        if "de3d" in scanning_sequence: #maybe scanning_sequence is Siemens-specific?
            return True

        return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        med_volume_out = group(med_volume, 'EchoTime')

        # rename flip angle. Maybe Siemens-specific again?
        med_volume_out.omids_header['PulseSequenceType'] = 'DESS'

        return med_volume_out

