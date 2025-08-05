from voxel import MedicalVolume as VoxelMedicalVolume
import copy

def copy_headers(medical_volume_src, medical_volume_dest):
    """ Copies the headers from one volume to another

    Parameters:
        medical_volume_src (MedicalVolume): the source volume
        medical_volume_dest (MedicalVolume): the destination volume

    Returns:
        No return value
    """
    for header in ['omids_header', 'meta_header', 'patient_header', 'extra_header']:
        setattr(medical_volume_dest, header, copy.deepcopy(getattr(medical_volume_src, header, None)))
    setattr(medical_volume_dest, 'bids_header', getattr(medical_volume_dest, 'omids_header')) # for compatibility


class OMidsMedVolume(VoxelMedicalVolume):
    """
    A MedicalVolume with additional attributes for OMids.
    This class is used to store the data and metadata of a medical volume in the OMids format.
    It extends the MedicalVolume class from the voxel package.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.omids_header = {}
        self.patient_header = {}
        self.extra_header = {}
        self.meta_header = {}
        self.bids_header = self.omids_header  # For compatibility with BIDS

    def _partial_clone(self, **kwargs):
        clone = super()._partial_clone(**kwargs)
        copy_headers(self, clone)
        return clone

MedicalVolume = OMidsMedVolume