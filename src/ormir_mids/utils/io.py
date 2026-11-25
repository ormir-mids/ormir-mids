import datetime
import json
import os
import re

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
    volume_list = dicom_reader.load(path)
    out = []
    for medical_volume in volume_list:
        setattr(medical_volume, 'path', path)
        new_volume = headers.dicom_volume_to_mids(medical_volume)
        if group_by is not None:
            new_volume = headers.group(new_volume, group_by)
        out.append(new_volume)
    return out


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
            new_volume = headers.dicom_volume_to_mids(volume)
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
    new_volume = headers.mids_volume_to_dicom(medical_volume, new_series)
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


def save_omids(nii_file, medical_volume, save_patient_json=True, save_extra_json=True, safe_save=True):
    """
    Saves a volume to a nifti file and its corresponding json files.

    Parameters:
        nii_file (str): Path to the nifti file
        medical_volume (MedicalVolume): The volume to save
        save_patient_json (bool): Save the patient json sidecar
        save_extra_json (bool): Save the extra/meta json sidecar
        safe_save (bool): If a dataset with the same name already exists, save the new one
            with the prefix tmp-[timestamp] instead of overwriting. Use clean_runs to
            disambiguate the datasets afterwards.

    Returns:
        None
    """
    if safe_save and os.path.exists(nii_file):
        timestamp = datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
        directory, file_name = os.path.split(nii_file)
        nii_file = os.path.join(directory, f'{TMP_PREFIX}{timestamp}_{file_name}')

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

TMP_PREFIX = 'tmp-'
_TMP_PATTERN = re.compile(r'^' + TMP_PREFIX + r'(\d{8}T\d+)_(.+)$')
_NII_PATTERN = re.compile(r'^(.+?)(\.nii\.gz|\.nii)$', re.IGNORECASE)
_RUN_PATTERN = re.compile(r'_run-(\d+)(?=_[^_]+$)')
_SIDECAR_SUFFIXES = ['.json', '_patient.json', '_extra.json']


def _split_nii(file_name):
    """Splits a nifti file name into (stem, extension). Returns None if it is not a nifti file."""
    match = _NII_PATTERN.match(file_name)
    if not match:
        return None
    return match.group(1), match.group(2)


def _add_run(stem, run):
    """Inserts the BIDS run- entity before the suffix (the last underscore-separated token)."""
    if '_' in stem:
        head, suffix = stem.rsplit('_', 1)
        return f'{head}_run-{run}_{suffix}'
    return f'run-{run}_{stem}'


def _series_number(path):
    """Returns the DICOM SeriesNumber (0020,0011) of an omids dataset, or None if unavailable."""
    try:
        volume = load_omids(path)
        value = headers.get_raw_tag_value(volume, '00200011')
        if isinstance(value, (list, tuple)):
            value = value[0]
        return int(value)
    except Exception:
        return None


def clean_runs(folder):
    """
    Disambiguates datasets saved by save_omids(safe_save=True) with the same target name.

    Finds datasets named tmp-[timestamp]_[name], loads them together with the base dataset
    [name] (and any dataset already carrying a run- entity), orders them by DICOM SeriesNumber
    (if available for all of them; otherwise the saving order is kept) and renames the nifti
    and json sidecar files adding the BIDS run-N entity before the suffix.

    Parameters:
        folder (str): Folder containing the datasets (not searched recursively)

    Returns:
        list: The final paths of the renamed nifti files
    """
    # group[(stem without run, extension)] = list of (order key, stem, path)
    groups = {}
    for file_name in sorted(os.listdir(folder)):
        split = _split_nii(file_name)
        if split is None:
            continue
        stem, ext = split
        tmp_match = _TMP_PATTERN.match(stem)
        if tmp_match:
            order = (1, tmp_match.group(1), 0)
            base_stem = tmp_match.group(2)
        else:
            run_match = _RUN_PATTERN.search(stem)
            base_stem = _RUN_PATTERN.sub('', stem)
            order = (0, '', int(run_match.group(1)) if run_match else 0)
        groups.setdefault((base_stem, ext), []).append((order, stem, os.path.join(folder, file_name)))

    renamed = []
    for (base_stem, ext), members in groups.items():
        if not any(_TMP_PATTERN.match(stem) for _, stem, _ in members):
            continue  # nothing to disambiguate
        members.sort(key=lambda m: m[0])  # existing runs/base first, then tmp in saving order
        numbers = [_series_number(path) for _, _, path in members]
        if all(n is not None for n in numbers):
            members = [m for _, m in sorted(zip(numbers, members), key=lambda x: x[0])]  # stable

        # two-step rename so that new names cannot clash with names that are still to be moved
        moves = []
        for run, (_, stem, path) in enumerate(members, start=1):
            new_stem = _add_run(base_stem, run)
            for suffix in [ext] + _SIDECAR_SUFFIXES:
                src = os.path.join(folder, stem + suffix)
                if os.path.exists(src):
                    moves.append((src, os.path.join(folder, new_stem + suffix)))
            renamed.append(os.path.join(folder, new_stem + ext))
        for i, (src, _) in enumerate(moves):
            os.rename(src, f'{src}.moving{i}')
        for i, (src, dst) in enumerate(moves):
            os.replace(f'{src}.moving{i}', dst)

    return renamed

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