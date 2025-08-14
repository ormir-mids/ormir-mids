from ..converter_base import Converter
from .MR import MRConverter
from ..utils import get_manufacturer


class GEMRConverter(Converter):
    @classmethod
    def get_name(cls):
        return 'MR'

    @classmethod
    def is_dataset_compatible(cls, med_volume):
        return 'GE' in get_manufacturer(med_volume).upper()

GEMRConverter.set_parent(MRConverter)