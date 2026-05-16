
# Copyright (c) Maria Monzon
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file_metadata except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import nibabel as nib
import numpy as np
import SimpleITK as sitk

 # Image Orientation planes and coordinates systems for MRI
 # Ref: http://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.2.html#sect_C.7.6.2.1.1
 #    [R] - Right - The direction in which X decreases.
 #    [L] - Left - The  direction in which X increases.
 #    [A] - Anterior - The  direction in which, Ydecreases.
 #    [P] - Posterior - The  direction in which Y  increases.
 #    [I|F] - Feet - The direction in which Z decreases.
 #    [S|H] - Head - The direction in which Z increases.


IMAGING_PLANES = ["SAGITTAL", "CORONAL", "AXIAL"]
IMAGING_PLANES_DICT = {"AXIAL": "ax", "CORONAL": "cor", "SAGITTAL": "sag",
                       "AXIAL-OBLIQUE": "ax-obl", "CORONAL-OBLIQUE": "cor-obl", "SAGITTAL-OBLIQUE": "sag-obl"}

ORIENTATION_LABELS = {  'RAS': (('L','R'),('P','A'),('I','S')),
                        'LPS': (('R','L'),('A','P'),('S','I')),
                        'LAS': (('R','L'),('S','I'),('A','P')),
                        'LAI': (('R','L'),('A','P'),('I','S')),
                        'RPS': (('L','R'),('A','P'),('S','I')),
                        'RAI': (('L','R'),('A','P'),('I','S')),
                        'RBD': (('L','R'),('S','I'),('P','A')),
                        'LBD': (('R','L'),('S','I'),('P','A'))
                    }

# Get equivalent direction for SITK orientation
DIRECTIONS = {'RAS':  (-1, 0, 0, 0, -1, 0, 0, 0, 1),
              'LPS':  (1, 0, 0, 0, 1, 0, 0, 0, 1),
              'LAS':  (1, 0, 0, 0, -1, 0, 0, 0, 1),
              'LAI':  (1, 0, 0, 0, -1, 0, 0, 0, -1),
              'RPS':  (-1, 0, 0, 0, 1, 0, 0, 0, 1),
              'RAI':  (-1, 0, 0, 0, 1, 0, 0, 0, -1),
              'RBD':  (-1, 0, 0, 0, 0, 1, 0, -1, 0),
              'LBD':  (1, 0, 0, 0, 0, 1, 0, -1, 0)}

def get_orientation_codes(image: nib.Nifti1Image) -> str:
    """ Get the orientation of the image
    Parameters:
    ----------
    image: nib.Nifti1Image
        image to extract orientations from

    Returns:
    --------
    orientations : (N,) tuple[str]
        labels for axis direction codes for affine Matrix
    """

    orientations = nib.aff2axcodes(image.affine)
    return orientations

def get_orientation(image: nib.Nifti1Image) -> str:
    """ Get the orientation of the image
    Parameters:
    ----------
    image: nib.Nifti1Image
        image to extract orientations from

    Returns:
    --------
    orientation : str
        orientation of the image
    """

    orientation = nib.aff2axcodes(image.affine)
    return ''.join(orientation)


def ensure_orientation(image: nib.Nifti1Image, orientation:str= 'RAS') -> nib.Nifti1Image:
    """ Ensure that the image is in the desired orientation (http://nipy.org/nibabel/image_orientation.html)

    Parameters:
    ----------
    image: nib.Nifti1Image
        image to be processed
    orientation: srt
         desired orientation axes: RAS (default),  LPS axes

    Returns:
    --------
    image: nib.Nifti1Image
        image in desired orientation
    """

    orientation = ORIENTATION_LABELS.get(orientation, ORIENTATION_LABELS['RAS'])

    orientation_codes = nib.aff2axcodes(image.affine)
    orientations = nib.orientations.axcodes2ornt(orientation_codes, orientation)
    image_data = image.get_fdata()
    image_data = nib.apply_orientation(image_data, orientations)
    image_nib = nib.Nifti1Image(image_data, image.affine, image.header)

    return image_nib


def image_to_RAS(image: nib.Nifti1Image) -> nib.Nifti1Image:
    """ Convert image to RAS orientation
    Parameters:
    ----------
    image: nib.Nifti1Image
        image to be processed
    Returns:
    --------
    ras_image: nib.Nifti1Image
        image in RAS orientation
    """
    return  nib.as_closest_canonical(image)


def get_imaging_plane(image_orientation_patient: list[float], patient_position:str = 'HFS') -> str:
    """ Helper function to determine the orientation of the MRI scanform the ImageOrientationPatient DICOM Tag.
    The image_array represents The direction cosines of the first row and the first column with respect to the patient.

    See https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.2.html#sect_C.7.6.2.1.1

    Parameters:
    -----------
    image_orientation_patient: list[float]
        The direction cosines of the first row and the first column with respect to the patient

    """

    IMAGING_PLANES =  ["SAGITTAL", "CORONAL", "AXIAL"]
    POSITIONS = {
        'HFS': (1, 1),  # No change
        'FFS': (1, -1),  # Flip the AP axis
        'HFP': (-1, -1)  # Flip both LR and AP axes
    }

    # Get adjustment factors based on patient position
    lr, ap = POSITIONS.get(patient_position, (1, 1))  # Default to no change

    # Adjust direction cosines based on patient position
    image_y = lr*np.array(image_orientation_patient[:3]) #image_orientation_patient[:3])   # image_orientation_patient[:3]
    image_x = ap*np.array(image_orientation_patient[3:])

    # Compute the cross product of between the volume_data dicom_slice
    image_z_components = abs(np.cross(image_x, image_y))

    # Retrieve what is the most prominent magnitude. This encodes if the MR is SAGITTAL,CORONAL,AXIAL
    imaging_plane = IMAGING_PLANES[list(image_z_components).index(max(image_z_components))]

    if not any(component >=0.97  for component in image_z_components):
        imaging_plane += "-OBLIQUE"

    return imaging_plane

def get_view_plane_short(plane: str) -> str:
    """ Get the string representation of the plane
    Parameters:
    ----------
    plane: str
        plane to be converted
    Returns:
    --------
    plane_str: str
        string representation of the plane
    """

    return IMAGING_PLANES_DICT.get(plane, "")



def extract_image_plane_from_description(description: str = ""):
    """ Helper function to find the ImageOrientationPatient description from the DICOM description tag.
    Parameters:
    -----------
    description: str
        The DICOM description tag
    Returns:
    --------
    orientation: str
        The orientation of the volume_data (AXIAL, CORONAL, SAGITTAL)
    """

    if str(description).find('AX') != -1 or str(description).find('TRA'):
        orientation = "AXIAL"
    elif str(description).find('COR') != -1:
        orientation = "CORONAL"
    elif str(description).find('SAG') != -1 or str(description).find('LONGIT'):
        orientation = "SAGITTAL"
    else:
        orientation = ""

    return orientation



def is_coordinate_system_LPS(image_orientation_patient: list[float], patient_position:str = 'HFS' ) -> bool:
    """
    Check if the coordinate system of a DICOM file is in LPS format.

    Parameters:
    ------------
    image_orientation_patient: list[float]
        The direction cosines of the first row and the first column with respect to the patient.
    patient_position: str
        The position of the patient in the scanner. Default is 'HFS'.

    Returns:
    ---------
    is_LPS:
        The coordinate system of the DICOM file. True if LPS, False otherwise.    """
    is_LPS = False

    # The direction cosines for the row (x) and column (y) axes
    cosines_x = image_orientation_patient[:3]
    cosines_y = image_orientation_patient[3:]
    # Check if the direction cosines correspond to the LPS coordinate system
    # In LPS, the x-axis is negative, y-axis is positive, and z-axis is positive
    if patient_position =='HFS':
        is_LPS = all([
            cosines_x[0] < 0, cosines_y[1] > 0,
            abs(cosines_x[2]) > 0 or abs(cosines_y[2]) > 0  # Check for non-zero z-component
        ])
    return is_LPS
