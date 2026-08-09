import json
import unittest.mock as mock

import numpy as np
import pytest
from helpers import check_nib_shape, zenodo_download_and_extract

from ormir_mids.converters.ct import ScancoConverter
from ormir_mids.dcm2omids import convert_dicom_to_ormirmids
from ormir_mids.utils.io import (
    UnsupportedScancoExtensionError,
    load_scanco,
    numpy_image_tuple,
    scanco_file_extensions,
)
from ormir_mids.utils.OMidsMedVolume import OMidsMedVolume


@pytest.fixture(scope="session")
def test_dirs(tmp_path_factory):
    """Create temporary directories for tests"""
    data_dir = tmp_path_factory.mktemp("test_data")
    output_dir = tmp_path_factory.mktemp("converted_data")
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {output_dir}")
    yield data_dir, output_dir


@pytest.fixture(scope="session")
def downloaded_data(test_dirs):
    """Download test data once for all tests"""
    data_dir, _ = test_dirs
    doi = r"https://doi.org/10.5281/zenodo.16763324"

    zenodo_download_and_extract(doi, data_dir)

    # Print directory contents
    files = list(data_dir.iterdir())
    print(f"\nFiles in {data_dir}:")
    for file in files:
        size = file.stat().st_size
        print(f"  - {file.name} ({size} bytes)")

    # Verify expected structure
    assert (
        data_dir / "XCTII-QC1-PHANTOM"
    ).exists(), "XCTII-QC1-PHANTOM directory not found"
    assert (data_dir / "md5sums.txt").exists(), "md5sums.txt file not found"

    # Return the path to the DICOM directory specifically
    phantom_dir = data_dir / "XCTII-QC1-PHANTOM"
    return phantom_dir


@pytest.fixture(scope="session")
def converted_data(downloaded_data, test_dirs):
    """Convert data once for all tests that need it"""
    _, output_dir = test_dirs
    dicom_dir = downloaded_data

    # Print what we're converting
    print(f"\nConverting data from: {dicom_dir}")
    print(f"Files in DICOM dir: {list(dicom_dir.iterdir())}")

    # Convert the data
    convert_dicom_to_ormirmids(
        dicom_dir,  # Use the specific DICOM directory
        output_dir,
        anonymize="anon",
        recursive=True,
    )

    print(f"\nOutput directory contents: {list(output_dir.iterdir())}")

    # Return the output path with converted data
    return output_dir


def test_download(downloaded_data):
    """Test that download worked correctly"""
    assert downloaded_data.exists()
    assert list(downloaded_data.iterdir()), "No files found in DICOM directory"


def test_convert(converted_data):
    """Test that conversion created the expected directory"""
    assert (
        converted_data / "sub-anon" / "ct"
    ).exists(), (
        f"Missing ct directory. Available directories: {list(converted_data.iterdir())}"
    )


def test_json(converted_data):
    """Test the JSON metadata"""
    omids_dir = converted_data / "sub-anon" / "ct"
    assert (
        omids_dir / "sub-anon_hrpqct.json"
    ).exists(), f"JSON file not found. Directory contents: {list(omids_dir.iterdir())}"

    # Check manufacturer and modality
    with open(omids_dir / "sub-anon_hrpqct.json", "r") as f:
        data = json.load(f)
    assert data["Manufacturer"] == "SCANCO Medical"
    assert data["Modality"] == "CT"


def test_nii(converted_data):
    """Test the NIfTI file"""
    omids_dir = converted_data / "sub-anon" / "ct"
    nii_file = omids_dir / "sub-anon_hrpqct.nii.gz"
    assert (
        nii_file.exists()
    ), f"NIfTI file not found. Directory contents: {list(omids_dir.iterdir())}"

    # Check shape
    nii_shape = (658, 658, 84)  # QC1 expected shape
    assert check_nib_shape(nii_file, nii_shape)


def test_compatibility_detection():
    """Test that ScancoConverter correctly identifies compatible datasets"""

    # Create mock MedicalVolume with Scanco headers and add required attributes
    mock_volume = mock.MagicMock(spec=OMidsMedVolume)
    mock_volume.omids_header = {}
    mock_volume.extra_header = {}  # Add this too as it might be needed
    mock_volume.patient_header = {}  # And this one

    # Test case 1: Valid Scanco CT
    with mock.patch("ormir_mids.converters.ct._is_ct", return_value=True), mock.patch(
        "ormir_mids.converters.ct.get_raw_tag_value", return_value=["SCANCO Medical"]
    ), mock.patch("ormir_mids.converters.ct._test_ima_type", return_value=True):
        assert ScancoConverter.is_dataset_compatible(mock_volume) is True

    # Test case 2: Not a CT scan - Mock get_raw_tag_value too since it's still called
    with mock.patch("ormir_mids.converters.ct._is_ct", return_value=False), mock.patch(
        "ormir_mids.converters.ct.get_raw_tag_value", return_value=["SOMETHING"]
    ):
        assert ScancoConverter.is_dataset_compatible(mock_volume) is False

    # Test case 3: CT but not Scanco
    with mock.patch("ormir_mids.converters.ct._is_ct", return_value=True), mock.patch(
        "ormir_mids.converters.ct.get_raw_tag_value",
        return_value=["Random Manufacturer"],
    ):
        assert ScancoConverter.is_dataset_compatible(mock_volume) is False


def test_load_scanco_missing_file(tmp_path):
    """A non-existent path should raise FileNotFoundError."""
    missing = tmp_path / "missing.aim"
    with pytest.raises(FileNotFoundError):
        load_scanco(missing)


def test_load_scanco_unsupported_extension(tmp_path):
    """An unsupported extension should raise UnsupportedScancoExtensionError."""
    bogus = tmp_path / "scan.xyz"
    bogus.touch()
    with pytest.raises(UnsupportedScancoExtensionError):
        load_scanco(bogus)


@pytest.mark.parametrize(
    "filename",
    ["scan.aim", "scan.isq", "scout.scv", "mask.gobj", "scan.AIM"],
)
def test_load_scanco_reads_supported_extensions(tmp_path, filename):
    """Any supported extension is forwarded to the single read_image dispatcher."""
    scanco_file = tmp_path / filename
    scanco_file.touch()
    with mock.patch(
        "ormir_mids.utils.io.read_scanco_image", return_value=("image", {"meta": 1})
    ) as mocked_reader:
        result = load_scanco(scanco_file)

    mocked_reader.assert_called_once_with(scanco_file)
    assert result == numpy_image_tuple("image", {"meta": 1})


def test_load_scanco_passes_kwargs_through(tmp_path):
    """Keyword arguments (e.g. density=True) must reach the underlying reader."""
    aim_file = tmp_path / "scan.aim"
    aim_file.touch()
    with mock.patch(
        "ormir_mids.utils.io.read_scanco_image", return_value=("image", {})
    ) as mocked_reader:
        load_scanco(aim_file, density=True)

    mocked_reader.assert_called_once_with(aim_file, density=True)


@pytest.mark.parametrize(
    "filename",
    ["scan.aim;3", "scan.isq;12", "scout.scv;7", "mask.gobj;1", "scan.AIM;3"],
)
def test_load_scanco_versioned_vms_paths(tmp_path, filename):
    """VMS-style paths carry a trailing `;<version>` suffix (e.g. "scan.aim;3").

    The extension must be resolved for dispatch, and the file must be opened
    using the original, unmodified path -- no renaming on disk.
    """
    versioned_file = tmp_path / filename
    versioned_file.touch()

    with mock.patch(
        "ormir_mids.utils.io.read_scanco_image", return_value=("image", {})
    ) as mocked_reader:
        load_scanco(versioned_file)

    mocked_reader.assert_called_once_with(versioned_file)
    # The original, version-suffixed file must still be present. Nothing was renamed.
    assert versioned_file.exists()


@pytest.fixture(scope="session")
def scanco_raw_data_dir(tmp_path_factory):
    """Download the raw Scanco record (real, unconverted AIM/ISQ/SCV/GOBJ files)."""
    data_dir = tmp_path_factory.mktemp("scanco_raw_data")
    doi = r"https://doi.org/10.5281/zenodo.4073082"
    zenodo_download_and_extract(doi, data_dir)
    return data_dir


@pytest.fixture(scope="session")
def first_scanco_image_path(scanco_raw_data_dir):
    """Locate the first Scanco-format file in the downloaded record, sorted by
    path for a deterministic pick. VMS version suffixes (e.g. ";1") are
    resolved with the same logic load_scanco itself uses."""
    candidates = sorted(
        p
        for p in scanco_raw_data_dir.rglob("*")
        if p.is_file() and p.suffix.lower().split(";", 1)[0] in scanco_file_extensions
    )
    assert candidates, (
        f"No Scanco-format files found in {scanco_raw_data_dir}. "
        f"Contents: {list(scanco_raw_data_dir.rglob('*'))}"
    )
    return candidates[0]
