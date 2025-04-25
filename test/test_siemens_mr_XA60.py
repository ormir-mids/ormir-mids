import pytest
from ormir_mids.dcm2omids import convert_dicom_to_ormirmids

from helpers import *

@pytest.fixture(scope="session")
def test_dirs(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("test_data")
    print(data_dir)
    output_dir = tmp_path_factory.mktemp("converted_data")
    print(output_dir)
    yield data_dir, output_dir
    #shutil.rmtree(data_dir)
    #shutil.rmtree(output_dir)

def test_download(test_dirs):
    data_dir, output_dir = test_dirs
    url = r'https://zenodo.org/records/14781472/files/ORMIR-MIDS_SampleData_MR_Siemens_XA60.zip?download=1'
    download_and_extract(url, data_dir)
    assert n_files_in_dir(data_dir) == 11

def test_convert(test_dirs):
    data_dir, output_dir = test_dirs
    convert_dicom_to_ormirmids(data_dir, output_dir, anonymize='anon', recursive=True, series_number=False, save_patient_json=True, save_extra_json=True)
    assert (output_dir / 'mr-anat').exists()
    assert n_files_in_dir(output_dir / 'mr-anat') == 12

def test_json(test_dirs):
    data_dir, output_dir = test_dirs
    omids_dir = output_dir / 'mr-anat'
    assert check_echo_times(omids_dir / 'anon_megre.json', [1.23, 2.46])
    assert check_echo_times(omids_dir / 'anon_megre_ph.json', [1.23, 2.46])
    assert check_echo_times(omids_dir / 'anon_mese.json', [11.0, 22.0, 33.0, 44.0, 55.0, 66.0, 77.0, 88.0,
                                                           99.0, 110.0, 121.0, 132.0, 143.0, 154.0, 165.0, 176.0, 187.0])

def test_nii(test_dirs):
    data_dir, output_dir = test_dirs
    omids_dir = output_dir / 'mr-anat'
    assert check_nib_shape(omids_dir / 'anon_megre.nii.gz', (104, 256, 150, 2))
    assert check_nib_shape(omids_dir / 'anon_megre_ph.nii.gz', (104, 256, 150, 2))
    assert check_nib_shape(omids_dir / 'anon_mese.nii.gz', (128, 256, 8, 17))