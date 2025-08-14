from ..converter_base.abstract_converter import RootConverter
from . import cr
from . import ct
from . import MR
from . import PhilipsMR
from . import SiemensMR
from . import GEMR
from . import dess_ge
from . import dess_siemens
from . import megre_ge
from . import megre_philips
from . import megre_siemens
from . import mese_ge
from . import mese_philips
from . import mese_siemens
from . import quantitative_maps

from .quantitative_maps import T1Converter, T2Converter, FFConverter, B0Converter, B1Converter

# print converter tree
def print_lineage(converter, level=0):
    if level == 5:
        return
    print('  ' * level + converter.get_name())
    for child in converter.get_children():
        print_lineage(child, level + 1)

print_lineage(RootConverter)