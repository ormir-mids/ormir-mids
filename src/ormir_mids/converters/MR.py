from ..utils.headers import get_modality
from ..converter_base import Converter, RootConverter

class MRConverter(Converter):

    @classmethod
    def get_name(cls):
        return 'MR'

    @classmethod
    def is_dataset_compatible(cls, med_volume):
        return 'MR' in get_modality(med_volume)

MRConverter.set_parent(RootConverter)