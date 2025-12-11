import json
import os

from voxel import DicomReader, DicomWriter, NiftiReader, NiftiWriter
from ..utils import headers


def load_dicom(path, group_by = None):
    """
    Loads all dicom files in a folder.

    Parameters:
        path (str): Path to the folder
        group_by (str): If not None, group the volumes by the specified header

    Returns:
        MedicalVolume with muscle-bids headers
    """
    dicom_reader = DicomReader(num_workers=0, group_by='SeriesInstanceUID', ignore_ext=True)
    medical_volume = dicom_reader.load(path)[0]
    setattr(medical_volume, 'path', path)
    new_volume = headers.dicom_volume_to_bids(medical_volume)
    if group_by is not None:
        new_volume = headers.group(new_volume, group_by)
    return new_volume


def load_dicom_with_subfolders(path):
    """
    Loads all dicom files in a folder and its subfolders.

    Parameters:
        path (str): Path to the root folder

    Returns:
        list: List of dicom volumes

    """
    dicom_reader = DicomReader(num_workers=0, group_by='SeriesInstanceUID', ignore_ext=True)
    def _read_dicom_recursive(rootdir):
        try:
            output_list = dicom_reader.load(rootdir)
        except (FileNotFoundError, KeyError):
            output_list = []
        for element in output_list:
            setattr(element, 'path', rootdir)
        for file in os.listdir(rootdir):
            d = os.path.join(rootdir, file)
            if os.path.isdir(d):
                print(d)
                output_list.extend(_read_dicom_recursive(d))
        return output_list

    med_volumes = _read_dicom_recursive(path)
    out = []
    for volume in med_volumes:
        try:
            new_volume = headers.dicom_volume_to_bids(volume)
        except:
            print("Warning: could not convert volume")
            continue
        out.append(new_volume)
    return out


def save_dicom(path, medical_volume, new_series = True):
    """
    Saves a volume to a folder.

    Parameters:
        path (str): Path to the folder
        medical_volume (MedicalVolume): The volume to save
        new_series (bool): If True, a new series is created

    Returns:
        None
    """
    new_volume = headers.bids_volume_to_dicom(medical_volume, new_series)
    #print(new_volume.headers().shape)
    dicom_writer = DicomWriter(num_workers=0)
    dicom_writer.save(new_volume, path)


def load_omids(nii_file):
    """
    Loads a nifti file and its corresponding json files.

    Parameters:
        nii_file (str): Path to the nifti file

    Returns:
        MedicalVolume: The loaded volume
    """
    nifti_reader = NiftiReader()
    medical_volume = nifti_reader.load(nii_file)
    json_base_name = nii_file

    # remove extensions
    if json_base_name.lower().endswith('.gz'):
        json_base_name = json_base_name[:-3]
    if json_base_name.lower().endswith('.nii'):
        json_base_name = json_base_name[:-4]

    try:
        with open(json_base_name + '.json', 'r') as f:
            omids_header = json.load(f)
    except FileNotFoundError:
        omids_header = {}

    try:
        with open(json_base_name + '_patient.json', 'r') as f:
            patient_header = json.load(f)
    except FileNotFoundError:
        patient_header = {}

    try:
        with open(json_base_name + '_extra.json', 'r') as f:
            extra_and_meta_header = json.load(f)
    except FileNotFoundError:
        extra_and_meta_header = {'extra': {}, 'meta': {}}

    setattr(medical_volume, 'meta_header', extra_and_meta_header['meta'])
    setattr(medical_volume, 'omids_header', omids_header)
    setattr(medical_volume, 'bids_header', omids_header) # for compatibility
    setattr(medical_volume, 'patient_header', patient_header)
    setattr(medical_volume, 'extra_header', extra_and_meta_header['extra'])

    return medical_volume


def save_omids(nii_file, medical_volume, save_patient_json=True, save_extra_json=True):
    """
    Saves a volume to a nifti file and its corresponding json files.

    Parameters:
        nii_file (str): Path to the nifti file
        medical_volume (MedicalVolume): The volume to save

    Returns:
        None
    """
    nifti_writer = NiftiWriter()
    nifti_writer.save(medical_volume, nii_file)
    json_base_name = nii_file

    # remove extensions
    if json_base_name.lower().endswith('.gz'):
        json_base_name = json_base_name[:-3]
    if json_base_name.lower().endswith('.nii'):
        json_base_name = json_base_name[:-4]

    extra_and_meta_header = {}

    extra_and_meta_header['meta'] = getattr(medical_volume, 'meta_header', {})
    extra_and_meta_header['extra'] = getattr(medical_volume, 'extra_header', {})
    omids_header = getattr(medical_volume, 'omids_header', {})
    patient_header = getattr(medical_volume, 'patient_header', {})

    with open(json_base_name + '.json', 'w') as f:
        json.dump(omids_header, f, indent=2)

    if save_patient_json:
        with open(json_base_name + '_patient.json', 'w') as f:
            json.dump(patient_header, f, indent=2)

    if save_extra_json:
        with open(json_base_name + '_extra.json', 'w') as f:
            json.dump(extra_and_meta_header, f, indent=2)

save_bids = save_omids

def find_omids(path, suffix):
    """
    Finds an ORMIR-MIDS dataset with a specific suffix (e.g. mese).

    Parameters:
        path (str): Path to the root folder
        suffix (str): Suffix of the bids dataset

    Returns:
        list: List of paths to the bids datasets
    """

    file_pattern = (suffix + '.nii.gz').lower()

    found_files = []

    for root, dirs, files in os.walk(path):
        for f in files:
            if f.lower().endswith(file_pattern):
                found_files.append(os.path.join(root, f))

    return found_files