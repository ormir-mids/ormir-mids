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
    url = r'https://zenodo.org/records/15282649/files/ORMIR_MIDS_SampleData_MR_PhilipsGE_MESE_MEGRE.zip?download=1'
    download_and_extract(url, data_dir)
    assert n_files_in_dir(data_dir) == 1

def test_convert(test_dirs):
    data_dir, output_dir = test_dirs
    convert_dicom_to_ormirmids(data_dir, output_dir, anonymize='anon', recursive=True, series_number=False, save_patient_json=True, save_extra_json=True)
    assert (output_dir / 'mr-anat').exists()
    assert (output_dir / 'mr-quant').exists()
    assert n_files_in_dir(output_dir / 'mr-anat') == 24
    assert n_files_in_dir(output_dir / 'mr-quant') == 4

def test_json(test_dirs):
    data_dir, output_dir = test_dirs
    omids_dir = output_dir / 'mr-anat'
    assert check_echo_times(omids_dir / 'anon_megre.json', [3.9, 6.3])
    assert check_echo_times(omids_dir / 'anon_megre_ph.json', [3.9, 6.3])
    assert check_echo_times(omids_dir / 'anon_mese.json', [8.0, 16.0, 24.0, 32.0, 40.0, 48.0, 56.0, 64.0,
                                                           72.0, 80.0, 88.0, 96.0, 104.0, 112.0, 120.0, 128.0, 136.0])

def test_nii(test_dirs):
    data_dir, output_dir = test_dirs
    omids_dir = output_dir / 'mr-anat'
    assert check_nib_shape(omids_dir / 'anon_megre.nii.gz', (256, 256, 32, 2))
    assert check_nib_shape(omids_dir / 'anon_megre_ph.nii.gz', (256, 256, 32, 2))
    assert check_nib_shape(omids_dir / 'anon_megre_real.nii.gz', (256, 256, 32, 2))
    assert check_nib_shape(omids_dir / 'anon_megre_imag.nii.gz', (256, 256, 32, 2))
    assert check_nib_shape(omids_dir / 'anon_mese.nii.gz', (176, 176, 6, 17))
    quant_dir = output_dir / 'mr-quant'
    assert check_nib_shape(quant_dir / 'anon_t2.nii.gz', (176, 176, 6))