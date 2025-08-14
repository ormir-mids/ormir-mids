from ..converter_base import Converter
from .MR import MRConverter
from ..utils import get_manufacturer


class PhilipsMRConverter(Converter):
    @classmethod
    def get_name(cls):
        return 'MR'

    @classmethod
    def is_dataset_compatible(cls, med_volume):
        return 'PHILIPS' in get_manufacturer(med_volume).upper()

PhilipsMRConverter.set_parent(MRConverter)