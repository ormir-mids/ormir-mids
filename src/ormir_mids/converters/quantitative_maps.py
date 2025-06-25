import os
from abc import abstractmethod

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, reduce, copy_volume_with_omids_headers


class AbstractQuantitativeConverter(Converter):

    @classmethod
    @abstractmethod
    def _get_tag(cls):
        pass

    @classmethod
    def get_name(cls):
        return cls._get_tag().upper()

    @classmethod
    def get_directory(cls):
        return os.path.join('mr-quant')

    @classmethod
    def get_file_name(cls, subject_id: str):
        return os.path.join(f'{subject_id}_{cls._get_tag()}')

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        if med_volume.ndim == 3:
            return True
        else:
            return False

    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        if med_volume.ndim == 4:
            med_volume_out = reduce(med_volume, 0)
        else:
            med_volume_out = copy_volume_with_omids_headers(med_volume)

        med_volume_out.omids_header['PulseSequenceType'] = f'{cls._get_tag().upper()} Map'

        return med_volume_out


class T2Converter(AbstractQuantitativeConverter):

    @classmethod
    def _get_tag(cls):
        return 't2'



class T1Converter(AbstractQuantitativeConverter):

    @classmethod
    def _get_tag(cls):
        return 't1'


class FFConverter(AbstractQuantitativeConverter):

    @classmethod
    def _get_tag(cls):
        return 'ff'


class B0Converter(AbstractQuantitativeConverter):

    @classmethod
    def _get_tag(cls):
        return 'b0'


class B1Converter(AbstractQuantitativeConverter):

    @classmethod
    def _get_tag(cls):
        return 'b1'

