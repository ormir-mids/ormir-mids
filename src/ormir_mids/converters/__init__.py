from ..converter_base.abstract_converter import Converter, RootConverter

# just importing all the converters builds the converter tree.
# If you create a new converter, make sure to import it here
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

# automatically import all Converters in this namespace
def _collect_subclasses(cls):
    result = []
    for sub in cls.__subclasses__():
        result.append(sub)
        result.extend(_collect_subclasses(sub))
    return result

for _cls in _collect_subclasses(Converter):
    globals()[_cls.__name__] = _cls

del _cls, _collect_subclasses

# print converter tree
def print_lineage(converter=RootConverter, level=0):
    print('  ' * level + converter.get_name())
    for child in converter.get_children():
        print_lineage(child, level + 1)

# Uncomment the line below to print the converter tree
# This can be useful for debugging or understanding the converter hierarchy.
# print_lineage()