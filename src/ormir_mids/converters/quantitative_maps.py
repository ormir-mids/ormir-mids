import os
from abc import abstractmethod

from ..converter_base.abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import reduce, copy_volume_with_omids_headers


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
    def get_suffix(cls):
        return f'_{cls._get_tag()}'

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
        return 'T2'



class T1Converter(AbstractQuantitativeConverter):

    @classmethod
    def _get_tag(cls):
        return 'T1'


class FFConverter(AbstractQuantitativeConverter):

    @classmethod
    def _get_tag(cls):
        return 'FF'


class B0Converter(AbstractQuantitativeConverter):

    @classmethod
    def _get_tag(cls):
        return 'B0'


class B1Converter(AbstractQuantitativeConverter):

    @classmethod
    def _get_tag(cls):
        return 'B1'
