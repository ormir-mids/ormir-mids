"""
This is the muscle-bids base package providing basic I/O functionality for reading and writing DICOM and BIDS files.
The python representation of the data is the MedicalVolume class, provided by pyvoxel, with added attributes for BIDS.


Specifically, the MedicalVolumes returned have four additional attributes:
    - omids_header: a dictionary containing the information contained in the BIDS header
    - patient_header: a dictionary containing patient information
    - extra_header: a dictionary containing raw DICOM tags that are not part of the BIDS header
    - meta_header: a dictionary containing the meta DICOM information
"""
from .utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from .utils.io import load_dicom, save_bids, load_dicom_with_subfolders, save_dicom, find_omids, save_omids

__all__ = ['load_dicom', 'save_bids', 'load_dicom_with_subfolders', 'save_dicom', 'find_omids']

__version__ = '0.1.2'