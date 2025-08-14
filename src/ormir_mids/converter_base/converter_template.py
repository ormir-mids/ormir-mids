import os

from .abstract_converter import Converter
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from ..utils.headers import get_raw_tag_value, group, get_manufacturer


# Note: the comments is in this module provide instructions on how to adapt the code to create a new converter. 


# In the class name below (SequenceConverterProducerMagnitude), change:
# - *Sequence* to your sequence name (E.g.: MeGre)
# - *Producer* name to your producer name (E.g.: GE)
# E.g.: SequenceConverterProducerMagnitude -> MeGreConverterGEMagnitude
class SequenceConverterProducerMagnitude(Converter):

    @classmethod
    def get_name(cls):
        
        # In the following string (sequence_producer_Magnitude), change: 
        # - *sequence* to your sequence name (E.g.: MeGre)
        # - *producer* to the producer name (E.g.: GE)
        # E.g.: 'sequence_producer_Magnitude' --> 'MeGre_GE_Magnitude'
        return 'sequence_producer_Magnitude'


    @classmethod
    def get_directory(cls):

        # If you images are not anatomical from MR, change the following string 'mr-anat' to:
        # - 'ct'
        # - others? 
        return 'mr-anat' 
    

    @classmethod
    def get_file_name(cls, subject_id: str):

        # In the following command, change: 
        # "sequence" to your sequence name (E.g.: MeGre)
        # Example: os.path.join(f'{subject_id}_sequence') -> os.path.join(f'{subject_id}_MeGre')
        return os.path.join(f'{subject_id}_sequence')
    

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):

        # The aim of this method is to identify the unique characteristics of your dataset, so that it can be extracted correctly form the larger dicom folder
        # The characteristics are unique combinations of values in the dicom header tags
        # You might need to use more than one conditions. 
        # Note the the following functions (get_raw_tag_value(), get_manufacturer()) are in the module utils/headers

        # Here are some examples of what you can check: 
        # Check if magnitude 'M' is the value of the tag '00080008' (get_raw_tag_value() gets the value of a tag)
        if 'M' not in get_raw_tag_value(med_volume, '00080008'):
            return False
        # Check if the producer is the expected one (get_manufacturer() returns the producer name)
        if 'GE' not in get_manufacturer(med_volume):
            return False
        # Check if the scanning sequence is the expected one ()
        if 'MeGre' not in get_raw_tag_value(med_volume, '00180024')[0]:
            return False
    
    
    @classmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        
        # the dicoms are grouped into separate files based on a characteristics ('Echo time' in this case)
        med_volume_out = group(med_volume, 'EchoTime')
        # add other information here?

        return med_volume_out
