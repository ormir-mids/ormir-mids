from ..converter_base import Converter
from .MR import MRConverter
from ..utils import get_manufacturer


class SiemensMRConverter(Converter):
    @classmethod
    def get_name(cls):
        return 'Siemens MR'

    @classmethod
    def is_dataset_compatible(cls, med_volume):
        return 'SIEMENS' in get_manufacturer(med_volume).upper()

SiemensMRConverter.set_parent(MRConverter)