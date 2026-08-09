import json
import unittest.mock as mock

import numpy as np
import pytest
from helpers import check_nib_shape, zenodo_download_and_extract

from py_aimio import (
    get_aim_density_equation,
    get_aim_hu_equation,
    get_isq_density_equation,
    get_isq_hu_equation,
)

from ormir_mids.converters.ct import ScancoConverter
from ormir_mids.dcm2omids import convert_dicom_to_ormirmids
from ormir_mids.utils.io import (
    UnsupportedScancoExtensionError,
    load_scanco,
    numpy_image_tuple,
    scanco_file_extensions,
)
from ormir_mids.utils.OMidsMedVolume import OMidsMedVolume
from ormir_mids.utils.scanco import _scanco_affine, jsonable, scanco_volume_to_mids


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


# --- scanco_volume_to_mids: field-to-file split -----------------------------------------
#
# Metadata below mirrors real py_aimio output (captured by reading actual .AIM/.ISQ files),
# with patient-identifying values replaced by fakes. Two real-world quirks are preserved
# deliberately, since they drive behavior in scanco_volume_to_mids:
#   - AIM nests most fields under processing_log; ISQ has them flat.
#   - AIM's spacing is in millimeters; ISQ's is in micrometers (unconverted by py_aimio).

_AIM_ARRAY_SHAPE = (2, 3, 4)  # (z, y, x), matching dimensions (4, 3, 2) below


def _aim_meta():
    processing_log_raw = (
        "! Processing Log\n"
        "!\n"
        "Created by                    ISQ_TO_AIM (IPL)\n"
        "Time                          16-APR-2017 20:20:59.67\n"
        "Original file                 dk0:[xtremect2.data.00001237.00005697]d0005679.isq;\n"
        "Original Creation-Date        14-SEP-2016 15:27:12.18\n"
        "Patient Name                                   DBQ_152\n"
        "Index Patient                                     1237\n"
        "Index Measurement                                5697\n"
        "Site                                               20\n"
        "Scanner ID                                       3401\n"
        "Scanner type                                        9\n"
        "Reconstruction-Alg.                                 3\n"
        "Energy [V]                                      68000\n"
        "Intensity [uA]                                   1470\n"
        "Integration time [us]                           43000\n"
        "Mu_Scaling                                       8192\n"
        "HU: mu water                                   0.2366\n"
        "Density: slope                             1662.52405\n"
        "Density: intercept                        -398.609009\n"
    )
    return {
        "filename": "/home/user/private_study/00001237/IMG1237.AIM",
        "version": 2,
        "id": 0,
        "reference": 0,
        "aim_type": 131074,
        "buffer_type": 2,
        "position": (1069, 541, 0),
        "dimensions": (4, 3, 2),
        "offset": (0, 0, 0),
        "element_size": (0.0607, 0.0607, 0.0607),
        "processing_log": {
            "Created by": "ISQ_TO_AIM (IPL)",
            "Time": "16-APR-2017 20:20:59.67",
            "Original file": "dk0:[xtremect2.data.00001237.00005697]d0005679.isq;",
            "Original Creation-Date": "14-SEP-2016 15:27:12.18",
            "Patient Name": "DBQ_152",
            "Index Patient": 1237,
            "Index Measurement": 5697,
            "Site": 20,
            "Scanner ID": 3401,
            "Scanner type": 9,
            "Reconstruction-Alg.": 3,
            "Energy [V]": 68000,
            "Intensity [uA]": 1470,
            "Integration time [us]": 43000,
            "Mu_Scaling": 8192,
            "HU: mu water": 0.2366,
            "Density: slope": 1662.52405,
            "Density: intercept": -398.609009,
            "Calibration Data": "68 kVp, BH: 200 mg HA/ccm, Scaling 8192, 0.2 CU",
        },
        "byte_offset": 3197,
        "spacing": (0.0607, 0.0607, 0.0607),
        "origin": (64.8879, 32.8385, 0.0),
        "vtkbone_origin": (64.9183, 32.8689, 0.0303),
        "direction": (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
        "processing_log_raw": processing_log_raw,
    }


def _isq_meta():
    return {
        "filename": "/home/user/private_study/00347/C0004378.ISQ",
        "version": 4,
        "data_type": 3,
        "nr_of_bytes": 1270877696,
        "nr_of_blocks": 2482183,
        "patient_index": 347,
        "scanner_id": 6020,
        "creation_date": (1872582144, 12304986),
        "dimensions": (4, 3, 2),
        "dimensions_p": (4, 3, 2),
        "dimensions_um": (137.6, 103.2, 68.8),
        "offset": (0, 0, 0),
        "spacing": (34.4, 34.4, 34.4),  # micrometers, unconverted by py_aimio
        "creation_date_string": " 8-MAY-2026 10:03:52.03\n",
        "slice_thickness_um": 34,
        "slice_increment_um": 34,
        "slice_1_pos_um": 40713,
        "min_data_value": -4111,
        "max_data_value": 32767,
        "mu_scaling": 4096,
        "nr_of_samples": 1024,
        "nr_of_projections": 250,
        "scandist_um": 35225,
        "scanner_type": 10,
        "sampletime_us": 200000,
        "index_measurement": 4559,
        "site": 4,
        "reference_line_um": 40713,
        "recon_alg": 3,
        "name": "BME_2026                               ",
        "energy": 70000,
        "intensity": 200,
        "holder": 10,
        "data_offset": 3584,
        "buffer_type": 0,
        "rescale_type": 1,
        "rescale_units": "mg HA/ccm",
        "rescale_slope": 373.335,
        "rescale_intercept": -194.278,
        "mu_water": 0.4792,
        "origin": (0.0, 0.0, 0.0),
        "direction": (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
        "unit": "native",
    }


def _load_scanco_volume(meta, filename):
    array = np.arange(np.prod(_AIM_ARRAY_SHAPE), dtype=np.int16).reshape(_AIM_ARRAY_SHAPE)
    with mock.patch(
        "ormir_mids.utils.scanco.load_scanco", return_value=(array, meta)
    ):
        return scanco_volume_to_mids(filename), array


def test_scanco_volume_to_mids_transposes_without_flipping():
    """volume[i,j,k] (x,y,z) must equal array[k,j,i] (z,y,x): a pure axis permutation, no reversal."""
    med_volume, array = _load_scanco_volume(_aim_meta(), "scan.AIM")
    assert med_volume.volume.shape == (4, 3, 2)
    for i in range(4):
        for j in range(3):
            for k in range(2):
                assert med_volume.volume[i, j, k] == array[k, j, i]


def test_scanco_affine_aim_is_already_millimeters():
    meta = _aim_meta()
    affine = _scanco_affine(meta)
    np.testing.assert_allclose(np.diag(affine)[:3], meta["spacing"])
    np.testing.assert_allclose(affine[:3, 3], meta["origin"])


def test_scanco_affine_isq_micrometers_converted_to_millimeters():
    """Regression test: py_aimio reports ISQ spacing in micrometers, unlike AIM's millimeters.
    Without conversion the affine would be 1000x too large."""
    meta = _isq_meta()
    affine = _scanco_affine(meta)
    expected_spacing_mm = np.array(meta["spacing"]) * 1e-3
    np.testing.assert_allclose(np.diag(affine)[:3], expected_spacing_mm)
    assert np.diag(affine)[0] < 1.0  # ~0.0344 mm, not ~34.4


def test_scanco_volume_to_mids_aim_field_split():
    med_volume, _ = _load_scanco_volume(_aim_meta(), "IMG1237.AIM")

    # main json: fields ScancoConverter.convert_dataset needs
    processing_log_raw = _aim_meta()["processing_log_raw"]
    expected_rescale_slope, expected_rescale_intercept = get_aim_hu_equation(processing_log_raw)
    expected_density_slope, expected_density_intercept = get_aim_density_equation(processing_log_raw)
    assert med_volume.omids_header == {
        "Modality": "CT",
        "Manufacturer": "SCANCO Medical",
        "RescaleSlope": expected_rescale_slope,
        "RescaleIntercept": expected_rescale_intercept,
        "ImageTypeSiemens": "DERIVED/PRIMARY/AXIAL",
        "XRayEnergy": 68.0,
        "XRayExposureTime": 43.0,
        "XRayExposure": pytest.approx(1470 * 43000 / 1e6),
        "ConvolutionKernel": "3",
        "ScancoMuScaling": 8192,
        "ScancoMuWater": 0.2366,
        "ScancoDensitySlope": expected_density_slope,
        "ScancoDensityIntercept": expected_density_intercept,
    }
    assert isinstance(med_volume.omids_header["ScancoMuScaling"], int)

    # patient json: identifying + location fields
    assert med_volume.patient_header == {
        "PatientName": "DBQ_152",
        "PatientID": "1237",
        "ScancoMeasurementIndex": "5697",
        "ScancoSite": "20",
        "ScannerID": "3401",
        "ScanDate": "20160914",
        "OriginalFile": "dk0:[xtremect2.data.00001237.00005697]d0005679.isq;",
    }

    # extra json: must not duplicate anything from main/patient, must not leak filename/raw log
    extra = med_volume.extra_header
    assert "filename" not in extra
    assert "processing_log_raw" not in extra
    for leaked_key in ("Patient Name", "Index Patient", "Index Measurement", "Site",
                       "Scanner ID", "Original file", "Original Creation-Date", "Time",
                       "Energy [V]", "Mu_Scaling", "Density: slope"):
        assert leaked_key not in extra["processing_log"]
    assert extra["processing_log"]["Calibration Data"] == "68 kVp, BH: 200 mg HA/ccm, Scaling 8192, 0.2 CU"
    assert extra["element_size"] == [0.0607, 0.0607, 0.0607]
    json.dumps(extra)  # must be json-safe

    assert med_volume.meta_header == {"SourceFormat": "SCANCO", "SourceFile": "IMG1237.AIM"}


def test_scanco_volume_to_mids_isq_field_split():
    meta = _isq_meta()
    med_volume, _ = _load_scanco_volume(meta, "C0004378.ISQ")

    expected_rescale_slope, expected_rescale_intercept = get_isq_hu_equation(meta)
    expected_density_slope, expected_density_intercept = get_isq_density_equation(meta)
    assert med_volume.omids_header == {
        "Modality": "CT",
        "Manufacturer": "SCANCO Medical",
        "RescaleSlope": expected_rescale_slope,
        "RescaleIntercept": expected_rescale_intercept,
        "ImageTypeSiemens": "ORIGINAL/PRIMARY/AXIAL",
        "XRayEnergy": 70.0,
        "XRayExposureTime": 200.0,
        "XRayExposure": pytest.approx(200 * 200000 / 1e6),
        "ConvolutionKernel": "3",
        "ScancoMuScaling": 4096,
        "ScancoMuWater": 0.4792,
        "ScancoDensitySlope": expected_density_slope,
        "ScancoDensityIntercept": expected_density_intercept,
    }
    assert isinstance(med_volume.omids_header["ScancoMuScaling"], int)

    assert med_volume.patient_header == {
        "PatientName": "BME_2026",
        "PatientID": "347",
        "ScancoMeasurementIndex": "4559",
        "ScancoSite": "4",
        "ScannerID": "6020",
        "ScanDate": "20260508",
    }
    assert "OriginalFile" not in med_volume.patient_header  # ISQ has no such field

    extra = med_volume.extra_header
    assert "filename" not in extra
    for leaked_key in ("name", "patient_index", "index_measurement", "site", "scanner_id",
                        "creation_date", "creation_date_string", "energy", "sampletime_us",
                        "mu_scaling", "mu_water", "rescale_slope", "rescale_intercept"):
        assert leaked_key not in extra
    assert extra["rescale_units"] == "mg HA/ccm"
    assert extra["slice_thickness_um"] == 34
    json.dumps(extra)

    assert med_volume.meta_header == {"SourceFormat": "SCANCO", "SourceFile": "C0004378.ISQ"}


def test_scanco_converter_accepts_aim_and_isq():
    aim_volume, _ = _load_scanco_volume(_aim_meta(), "scan.AIM")
    isq_volume, _ = _load_scanco_volume(_isq_meta(), "scan.ISQ")

    assert ScancoConverter.is_dataset_compatible(aim_volume) is True
    assert ScancoConverter.is_dataset_compatible(isq_volume) is True


def test_jsonable_handles_numpy_scalars_tuples_and_nested_dicts():
    payload = {"a": np.float32(1.5), "b": (1, 2, np.int64(3)), "c": {"d": None}}
    result = jsonable(payload)
    json.dumps(result)
    assert result["a"] == pytest.approx(1.5)
    assert result["b"] == [1, 2, 3]
    assert result["c"] == {"d": None}
