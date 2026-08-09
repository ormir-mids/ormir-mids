import datetime
from pathlib import Path

import numpy as np
from py_aimio import (
    get_aim_density_equation,
    get_aim_hu_equation,
    get_isq_density_equation,
    get_isq_hu_equation,
)

from .io import load_scanco
from .OMidsMedVolume import OMidsMedVolume as MedicalVolume

# AIM's processing_log and ISQ's flat meta dict use different field names for the same
# concepts, so patient-identifying and main-header fields are tracked per format. Anything
# not in either set below ends up in extra_header.
_AIM_PATIENT_LOG_KEYS = {
    "Patient Name", "Index Patient", "Index Measurement", "Site", "Scanner ID",
    "Original Creation-Date", "Time", "Original file",
}
_AIM_MAIN_LOG_KEYS = {
    "Energy [V]", "Integration time [us]", "Intensity [uA]", "Reconstruction-Alg.",
    "Mu_Scaling", "HU: mu water", "Density: slope", "Density: intercept",
}
_ISQ_PATIENT_KEYS = {
    "name", "patient_index", "index_measurement", "site", "scanner_id",
    "creation_date", "creation_date_string",
}
_ISQ_MAIN_KEYS = {
    "energy", "sampletime_us", "intensity", "recon_alg", "mu_scaling", "mu_water",
    "rescale_slope", "rescale_intercept",
}

_SCANCO_DATE_FORMATS = ("%d-%b-%Y", "%Y-%m-%d")


def _num(value, default=0.0):
    """ Best-effort float conversion, falling back to a default instead of raising """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default=0):
    """ Best-effort int conversion, falling back to a default instead of raising """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def jsonable(value):
    """ Coerces aimio-py metadata (numpy scalars, tuples, nested dicts) into something json.dump can handle

    Parameters:
        value (Any): the value to coerce

    Returns:
        Any: a value made only of dict/list/str/int/float/bool/None
    """
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    return str(value)


def _is_aim_meta(meta):
    """ Distinguishes AIM metadata (nested under processing_log) from flat ISQ metadata """
    return "processing_log" in meta


def _scanco_date(value):
    """ Normalizes a Scanco date string to DICOM-style YYYYMMDD

    Handles AIM's "14-SEP-2016 15:27:12.18" and ISQ's " 8-MAY-2026 10:03:52.03\\n", both of
    which carry the date as the first whitespace-separated token.

    Parameters:
        value (Any): the raw date value from Scanco metadata

    Returns:
        str: the date as YYYYMMDD, or an empty string if it could not be parsed
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    token = text.split()[0]
    for fmt in _SCANCO_DATE_FORMATS:
        try:
            return datetime.datetime.strptime(token, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    return ""


_MICRON_TO_MM = 1e-3


def _scanco_affine(meta):
    """ Builds a 4x4 affine from the geometry aimio-py already computes (DICOM/LPS convention, no ITK needed)

    aimio-py's AIM reader reports spacing/origin in millimeters, but its ISQ reader reports
    them in micrometers (verified against real files: ISQ spacing equals dimensions_um /
    dimensions, unconverted). Both are normalized to millimeters here.

    Parameters:
        meta (dict): Scanco metadata, as returned by load_scanco

    Returns:
        np.ndarray: a 4x4 affine matrix, in millimeters
    """
    spacing = np.asarray(meta["spacing"], dtype=float)
    origin = np.asarray(meta["origin"], dtype=float)
    if not _is_aim_meta(meta):
        spacing = spacing * _MICRON_TO_MM
        origin = origin * _MICRON_TO_MM
    direction = np.asarray(meta["direction"], dtype=float).reshape(3, 3)
    affine = np.eye(4)
    affine[:3, :3] = direction @ np.diag(spacing)
    affine[:3, 3] = origin
    return affine


def _build_main_header(meta):
    """ Builds the omids_header: fields needed for a good conversion, mirroring what
    ScancoConverter.convert_dataset (converters/ct.py) expects

    Parameters:
        meta (dict): Scanco metadata, as returned by load_scanco

    Returns:
        dict: the omids_header
    """
    header = {
        "Modality": "CT",
        "Manufacturer": "SCANCO Medical",
    }

    if _is_aim_meta(meta):
        log = meta.get("processing_log", {})
        header["ImageTypeSiemens"] = "DERIVED/PRIMARY/AXIAL"
        header["XRayEnergy"] = _num(log.get("Energy [V]")) / 1000.0
        header["XRayExposureTime"] = _num(log.get("Integration time [us]")) / 1000.0
        header["XRayExposure"] = (
            _num(log.get("Intensity [uA]")) * _num(log.get("Integration time [us]")) / 1e6
        )
        header["ConvolutionKernel"] = str(log.get("Reconstruction-Alg.", ""))
        header["ScancoMuScaling"] = _int(log.get("Mu_Scaling"))
        header["ScancoMuWater"] = _num(log.get("HU: mu water"))
        processing_log_raw = meta.get("processing_log_raw", "")
        rescale_slope, rescale_intercept = get_aim_hu_equation(processing_log_raw)
        density_slope, density_intercept = get_aim_density_equation(processing_log_raw)
    else:
        header["ImageTypeSiemens"] = "ORIGINAL/PRIMARY/AXIAL"
        header["XRayEnergy"] = _num(meta.get("energy")) / 1000.0
        header["XRayExposureTime"] = _num(meta.get("sampletime_us")) / 1000.0
        header["XRayExposure"] = (
            _num(meta.get("intensity")) * _num(meta.get("sampletime_us")) / 1e6
        )
        header["ConvolutionKernel"] = str(meta.get("recon_alg", ""))
        header["ScancoMuScaling"] = _int(meta.get("mu_scaling"))
        header["ScancoMuWater"] = _num(meta.get("mu_water"))
        rescale_slope, rescale_intercept = get_isq_hu_equation(meta)
        density_slope, density_intercept = get_isq_density_equation(meta)

    # Voxels stay in native units. RescaleSlope/RescaleIntercept give the standard DICOM
    # CT conversion to Hounsfield Units; ScancoDensitySlope/ScancoDensityIntercept give the
    # Scanco-specific conversion to BMD (no DICOM-standard equivalent).
    header["RescaleSlope"] = rescale_slope
    header["RescaleIntercept"] = rescale_intercept
    header["ScancoDensitySlope"] = density_slope
    header["ScancoDensityIntercept"] = density_intercept
    return header


def _build_patient_header(meta):
    """ Builds the patient_header: identifying and scan-location fields, kept out of
    omids_header/extra_header so they can be excluded from output independently
    (save_patient_json=False)

    Parameters:
        meta (dict): Scanco metadata, as returned by load_scanco

    Returns:
        dict: the patient_header
    """
    if _is_aim_meta(meta):
        log = meta.get("processing_log", {})
        header = {
            "PatientName": str(log.get("Patient Name", "")).strip(),
            "PatientID": str(log.get("Index Patient", "")),
            "ScancoMeasurementIndex": str(log.get("Index Measurement", "")),
            "ScancoSite": str(log.get("Site", "")),
            "ScannerID": str(log.get("Scanner ID", "")),
            "ScanDate": _scanco_date(log.get("Original Creation-Date") or log.get("Time")),
        }
        original_file = log.get("Original file")
        if original_file:
            header["OriginalFile"] = str(original_file)
        return header

    return {
        "PatientName": str(meta.get("name", "")).strip(),
        "PatientID": str(meta.get("patient_index", "")),
        "ScancoMeasurementIndex": str(meta.get("index_measurement", "")),
        "ScancoSite": str(meta.get("site", "")),
        "ScannerID": str(meta.get("scanner_id", "")),
        "ScanDate": _scanco_date(meta.get("creation_date_string")),
    }


def _build_extra_header(meta):
    """ Builds the extra_header: remaining technical metadata, minus fields promoted to
    omids_header/patient_header and minus leak vectors (`filename` is a full local path;
    `processing_log_raw` duplicates patient fields as plain text even after the parsed
    processing_log dict is scrubbed)

    Parameters:
        meta (dict): Scanco metadata, as returned by load_scanco

    Returns:
        dict: the extra_header, safe to json.dump
    """
    if _is_aim_meta(meta):
        extra = {
            k: v for k, v in meta.items()
            if k not in ("filename", "processing_log", "processing_log_raw")
        }
        extra["processing_log"] = {
            k: v for k, v in meta.get("processing_log", {}).items()
            if k not in _AIM_PATIENT_LOG_KEYS and k not in _AIM_MAIN_LOG_KEYS
        }
    else:
        extra = {
            k: v for k, v in meta.items()
            if k not in _ISQ_PATIENT_KEYS and k not in _ISQ_MAIN_KEYS and k != "filename"
        }
    return jsonable(extra)


def scanco_volume_to_mids(path, **kwargs):
    """
    Reads a Scanco AIM/ISQ/SCV/GOBJ file and builds an OMidsMedVolume from it.

    Parameters:
        path (str or pathlib.Path): Path to the Scanco file.
        **kwargs: Additional keyword arguments passed to load_scanco (e.g. unit="hu" for
            ISQ, density=True for AIM).

    Returns:
        OMidsMedVolume: the volume, with omids_header, patient_header, extra_header and
            meta_header populated.
    """
    image, meta = load_scanco(path, **kwargs)
    volume = np.transpose(image, (2, 1, 0))  # (z,y,x) -> (x,y,z), no flip needed
    affine = _scanco_affine(meta)

    med_volume = MedicalVolume(volume, affine)
    med_volume.path = str(path)
    med_volume.omids_header = _build_main_header(meta)
    med_volume.bids_header = med_volume.omids_header
    med_volume.patient_header = _build_patient_header(meta)
    med_volume.extra_header = _build_extra_header(meta)
    med_volume.meta_header = {
        "SourceFormat": "SCANCO",
        "SourceFile": Path(path).name,
    }
    return med_volume