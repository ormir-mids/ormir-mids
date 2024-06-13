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

# -*- coding: utf-8 -*-
__author__ = "Maria Monzon"
__version__ = "0.1.0"


import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
import nibabel as nib
import pandas as pd
import numpy as np
import shutil
import SimpleITK as sitk
from ..utils.files import load_json, save_json
from ..utils.strings import extract_number


MR_ANAT_MODALITIES = ["T1w", "T2w", "T2star", "FLAIR", "PD", "PDT2", "inplaneT1"]
LOC_MOD = ["loc", "localizer*"]

MODALITIES = {
    "anat" : '|'.join(MR_ANAT_MODALITIES),
    "loc" : '|'.join(LOC_MOD)
}


PARTICIPANTS_FIELDS = {
    "participant_id": {
        "LongName": "Participant ID",
        "Description": "A unique identifier for each participant in the study.",
    },
    "age": {
        "LongName": "Age",
        "Description": "The age of the participant in years relative to the date of birth.",
        "Units": "years",
    },
    "sex": {
        "LongName": "Sex",
        "Description": "The sex of the participant as reported by the participant.",
        "Levels": {
            "M": "male",
            "F": "female",
        },
    },
    "modalities": {
        "LongName": "Modalities",
        "Description": "The imaging modalities used in the study.",
    },
    "body_parts": {
        "LongName": "Body Parts",
        "Description": "The body parts imaged in the study",
    },
}

SESSION_FIELDS = {

    "session_id": {
        "LongName": "Session ID",
        "Description": "A unique identifier for each imaging session in the study.",
    },

    "study_uid": {
        "LongName": "Study UID",
        "Description": "A unique identifier for the study that the session belongs to.",
    },
    "acquisition_date": {
        "LongName": "Acquisition Date and Time",
        "Description": "The date and time when the imaging session was acquired.",
    },
    "radiology_report": {
        "LongName": "Radiology Report",
        "Description": "A report containing the interpretation and findings of the imaging session by a radiologist.",
    },
}
NIFTY_FIELDS = {
    'pixdim': "PixelSpacing",
    'dim': "Dimensions",
    'sform_code': "CoordinateSystem",
    'scl_inter': "RescaleIntercept",
    'scl_slope': "RescaleSlope",
}

SCANS_MR_FIELDS = {
    "scan_file": {
        "LongName": "Scan File",
        "Description": "The file name of the scan",
    },
    "BodyPart": {
        "LongName": "Body Part Examined Attribute Tag (0018,0015)",
        "Description": "The part of the body examined in the scan.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/general-series/00180015"
    },
    "Modality": {
        "LongName": "Acquisition Modality (0008,0060)",
        "Description": "Type of device, process or method that originally acquired ",
        "TermURL": "https://dicom.innolitics.com/ciods/segmentation/general-series/00080060"
    },
    "SeriesDescription": {
        "LongName": "Series Description (0008,103E)",
        "Description": "A description of the series.",
        "TermURL": "https://dicom.innolitics.com/ciods/ct-image/general-series/0008103e"
    },
    "SeriesNumber": {
        "LongName": "Series Number Attribute Tag (0020,0011)",
        "Description": "A number that identifies the series.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/general-series/00200011"
    },
    "PixelSpacing": {
        "LongName": "Pixel Spacing (0028,0030)",
        "Description": "Physical distance between the center of each pixel, specified by a numeric pair - adjacent row spacing (delimiter) adjacent column spacing in mm.",
        "DICOM Tag": "(0028,0030)",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00280030"
    },
    "RepetitionTime": {
        "LongName": "Repetition Time (0018,0080)",
        "Description": "Time in seconds between the beginning of a pulse sequence and the beginning of the succeeding (identical) pulse sequence.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180080"
    },
    "EchoTime": {
        "LongName": "Echo Time (0018,0081)",
        "Description": "Time in milliseconds between the middle of the excitation pulse and the peak of the echo produced.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180081"
    },
    "InversionTime": {
        "LongName": "Inversion Time (0018,0082)",
        "Description": "Time in milliseconds after the inversion pulse.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180082"
    },

    "SliceThickness": {
        "LongName": "Slice Thickness (0018,0050)",
        "Description": "Nominal slice thickness, in mm.",
        "DICOM Tag": "(0018,0050)",
        "TermURL": "https://dicom.innolitics.com/ciods/rt-dose/image-plane/00180050"
    },
    "SpacingBetweenSlices": {
        "LongName": "Spacing Between Slices (0018,0088)",
        "Description": "Spacing between slices, in mm. The spacing is measured from the center-to-center of each slice.",
        "TermURL": "https://dicom.innolitics.com/ciods/ct-performed-procedure-protocol/performed-ct-reconstruction/00189934/00180088"
    },
    "SeriesInstanceUID": {
        "LongName": "Series Instance UID Attribute Tag (0020,000E)",
        "Description": "A unique identifier for the series.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/general-series/0020000E"
    },
    "MRAcquisitionType": {
        "LongName": "MR Acquisition Type (0018,0023)",
        "Description": "Specifies the type of MR acquisition.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180023"
    },
    "MagneticFieldStrength": {
        "LongName": "Magnetic Field Strength Attribute Tag (0018,0087)",
        "Description": "The strength of the magnetic field in Tesla.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180087"
    },
    "ScanningSequence": {
        "LongName": "Scanning Sequence (0018,0020)",
        "Description": "Specifies the type of MR scanning sequence used.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180020"
    },
    "SequenceVariant": {
        "LongName": "Sequence Variant (0018,0021)",
        "Description": "Specifies the variant of the scanning sequence.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180021"
    },
    "ScanOptions": {
        "LongName": "Scan Options (0018,0022)",
        "Description": "Specifies additional options for the scanning sequence.",
        "TermURL": "https://dicom.innolitics.com/ciods/ct-image/ct-image/00180022"
    },
    "SequenceName": {
        "LongName": "Sequence Name (0018,0024)",
        "Description": "User-defined name for the combination of Scanning Sequence and Sequence Variant.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180024"
    },
    "SliceEncodingDirection": {
        "LongName": "Slice Encoding Direction (0018,1312)",
        "Description": "Direction in which slices are encoded.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00181312"
    },
    "FlipAngle": {
        "LongName": "Flip Angle (0018,1314)",
        "Description": "Angle in degrees of the excitation pulse.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00181314"
    },
    "EchoNumbers": {
        "LongName": "Echo Numbers (0018,0086)",
        "Description": "Number of echoes in multi-echo sequences.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180086"
    },
    "EchoTrainLength": {
        "LongName": "Echo Train Length (0018,0091)",
        "Description": "Number of lines in k-space acquired per excitation per image.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180091"
    },
    "ImagedNucleus": {
        "LongName": "Imaged Nucleus (0018,0085)",
        "Description": "Nucleus that is resonant at the imaging frequency.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180085"
    },
    "ImagingFrequency": {
        "LongName": "Imaging Frequency (0018,0084)",
        "Description": "Precession frequency in MHz of the nucleus being addressed.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180084"
    },
    "InPlanePhaseEncodingDirection": {
        "LongName": "In-plane Phase Encoding Direction (0018,1312)",
        "Description": "The axis of phase encoding with respect to the image.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00181312"
    },
    "NumberOfPhaseEncodingSteps": {
        "LongName": "Number of Phase Encoding Steps (0018,0089)",
        "Description": "Number of phase encoding steps along the phase encoding direction before Fourier transformation.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180089"
    },
    "PercentPhaseFieldOfView": {
        "LongName": "Percent Phase Field of View (0018,0094)",
        "Description": "Percentage of the field of view dimension in the phase direction relative to the frequency direction.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180094"
    },
    "PercentSampling": {
        "LongName": "Percent Sampling (0018,0093)",
        "Description": "Percentage of sampling of data acquired in the frequency direction.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180093"
    },
    "PhotometricInterpretation": {
        "LongName": "Photometric Interpretation (0028,0004)",
        "Description": "Specifies the intended interpretation of the pixel data.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00280004"
    },
    "PixelBandwidth": {
        "LongName": "Pixel Bandwidth (0018,0095)",
        "Description": "Bandwidth per pixel in the phase encode direction.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180095"
    },

    "SAR": {
        "LongName": "Specific Absorption Rate (0018,1316)",
        "Description": "Rate at which RF energy is absorbed by the body during an MR procedure.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00181316"
    },
    "SamplesPerPixel": {
        "LongName": "Samples per Pixel (0028,0002)",
        "Description": "Number of samples (data points) stored for each pixel in the image.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00280002"
    },
    "Manufacturer": {
        "LongName": "Manufacturer (0008,0070)",
        "Description": "Manufacturer of the equipment that produced the composite instances.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00080070"
    },
    "ManufacturerModelName": {
        "LongName": "Manufacturer's Model Name Attribute Tag (0008,1090)",
        "Description": "The model name of the imaging equipment.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/general-equipment/00081090"
    },
    "ReceiveCoilName": {
        "LongName": "Receive Coil Name Attribute Tag (0018,1250)",
        "Description": "The name of the coil that receives the MR signal.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00181250"
    },

    "TransmitCoilName": {
        "LongName": "Transmit Coil Name (0018,1251)",
        "Description": "The name of the coil used in transmission.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00181251"
    },
    "PulseSequenceDetails": {
        "LongName": "Pulse Sequence Details (0018,9005)",
        "Description": "Provides details about the pulse sequence used in MR imaging.",
        "TermURL": "https://dicom.innolitics.com/ciods/enhanced-mr-image/mr-pulse-sequence/00189005"
    },

    "PulseSequenceName": {
        "LongName": "Pulse Sequence Name Attribute Tag	(0018,9005)",
        "Description": "Name of the pulse sequence for annotation purposes",
        "TermURL": "https://dicom.innolitics.com/ciods/enhanced-mr-image/mr-pulse-sequence/00189005"
    },
    "SliceTiming": {
        "LongName": "Slice Timing (0018,0091)",
        "Description": "Time at which each slice was acquired.",
        "TermURL": "https://dicom.innolitics.com/ciods/mr-image/mr-image/00180091"
    },
    "WindowCenter": {
        "LongName": "Window Center (0028,1050)",
        "Description": "The center of the window used for display.",
        "TermURL": "https://dicom.innolitics.com/ciods/ct-image/voi-lut/00281050"
    },
    "WindowWidth": {
        "LongName": "Window Width (0028,1051)",
        "Description": "The width of the window used for display.",
        "TermURL": "https://dicom.innolitics.com/ciods/ct-image/voi-lut/00281051"
    },
    "SpecificCharacterSet": {
        "LongName": "Specific Character Set (0008,0005)",
        "Description": "Specifies the character set that is used to encode strings in the DICOM dataset.",
        "TermURL": "https://dicom.innolitics.com/ciods/ct-image/sop-common/00080005"
    },
    "SoftwareVersions": {
        "LongName": "Software Versions (0018,1020)",
        "Description": "A string that represents the version of the software.",
        "TermURL": "https://dicom.innolitics.com/ciods/ct-image/general-equipment/00181020"
    }

}
participants_header = list(PARTICIPANTS_FIELDS.keys()) # ['participant_id',  'age', 'sex',  'modalities', 'body_parts' ]
participants_keys = ['PatientID' , 'PatientBirthDate', 'PatientSex', 'Modality', 'BodyPartExamined']
session_header = list( SESSION_FIELDS.keys())  #['session_id' ,'study_uid', 'acquisition_date' ,'radiology_report']
sessions_keys = ['StudyInstanceUID', 'AcquisitionDateTime']
scans_header_mr = list(SCANS_MR_FIELDS.keys())
scans_header_micr = ['scan_file' ,
                     'BodyPart',
                     'SeriesNumber',
                     'SeriesInstanceUID',
                     'Manufacturer'
                     ,'ManufacturerModelName',
                     'Modality',
                     'Columns',
                     'Rows',
                     'PhotometricInterpretation'
                     ,'ImagedVolumeHeight',
                     'ImagedVolumeHeight']
scans_header_op = ['scan_file',
                   'BodyPart',
                   'SeriesNumber',
                   'SeriesInstanceUID',
                   'Manufacturer' ,
                   'ManufacturerModelName',
                   'Modality',
                   'Columns' ,
                   'Rows',
                   'PhotometricInterpretation',
                   'Laterality',
                   'note']
chunk_pattern = re.compile(r"_chunk-(?P<chunk>\d)+")

def create_dataset_description_json(metadata_dict: dict, output_path:[Path | None] = None, contributors: list = []) -> dict:
    """Creates a dataset_description.json file from YAML metadata.

    Parameters
    ----------
    metadata_dict: dict
        dictionary with the metadata of the keys:
        {
          Name: 'Dataset Name'
          DatasetType: "raw",
          Date: "YYYY-MM-DD"                # Date of the dataset creation
          Version: "1.0"                    # version of the dataset
          Description: "Basic Description of the dataset in the form "
          License: "CC BY-NC-SA 4.0"
          Doi: " " # DOI of the dataset
          Reference: " Url of the dataset info page"
          BIDSVersion: "" # BIDS version of the dataset,
          Authors: [
            "Author1",
            "Author2"
          ]
          Acknowledgements: "Special thanks to all the contributors of the dataset"
          Citation: # citation of the dataset in bibtex format
            - "@misc {id,
                        author       = { },
                        title        = { },
                        month        =  ,
                        year         =  ,
                        publisher    = { },
                        doi          = { },
                        url          = { }}"

          Download:
            URL: # list of urls to download the dataset
              - "https:/XXXXXXXXX?download=1"
            checksum : # list of checksums for the downloaded files
            - ""
            hash_type: ["md5"]
          Size: 0.25    #Size of the dataset in GB
          Nfiles: 447   # Number of files in the dataset excluding metadata files

          Modality: "MR"                      # DICOM Modality Attribute
          ModalityType: [ "T1w", "T2w"]       # BIDS Modality of the data
          DataType: "anat"
          Metadata: ["patients.csv", "overview.csv"]  # metadata files
          Extension: '.mha'                   # extension of the images and labels

          Dimension: [ "3D", "2D"]            # Data Dimension:  MRAcquisitionType
          CoordinateSystem: ['LPS']           # Image Orientation Attribute
          ImagePlane: ["sagittal", "axial"]   # MRI acquisition planes
          #   PatientPosition : ['HFS']   # Image Orientation Attribute
          BodyPartExamined: ["LSSPINE"]

          # Tags Related to algorithm training
          Task: "Segmentation"              # Task for which the dataset is used
          Labels: { "BG": 0,        # labels names and their corresponding values
                    "L5": 1,
                    "L4": 2,
                    "L3": 3,
                    "L2": 4,
                    "L1": 5 }

          PathPatterns:
          - images:  "/images/*"          # pattern to search for images
          - labels:  "/masks/*"           # pattern to search for labels
        }

    output_path: Path or None (optional)
        path to the output file

    """

    dataset_description = {
        "Name":  metadata_dict.get("Name", ""), #"The mother of all experiments",
        "BIDSVersion": metadata_dict.get("BIDSVersion", "1.9.0"),
        "DatasetType": metadata_dict.get("DatasetType", "mids"),
        "License": metadata_dict.get("License", "CC BY-NC-SA 4.0"),
        "Authors": metadata_dict.get('Authors', "Author1, Author2"),
        "Acknowledgements": metadata_dict.get('Acknowledgements', "Special thanks to the contributors of this dataset"),
        "HowToAcknowledge": f"Please cite the papers",
        "ReferencesAndLinks": [
            metadata_dict.get('Reference',  metadata_dict.get('Download', "").get('URL', [""]))
        ],
        "DatasetDOI": metadata_dict.get('Doi', "doi: "),

        "GeneratedBy": [
            {
                "Name": f"{contributors}",
                "Version": ""
            }
        ],
        "SourceDatasets": [
            {
                "URL": metadata_dict.get( 'Download', {} ).get('URL',  [  metadata_dict.get('Reference', "") ] )[0],
                "Version": metadata_dict.get('Version', "1.0"),
            }
        ]
    }
    duplicate_keys = ["Name", "BIDSVersion", "DatasetType", "License", "Authors",
                      "Acknowledgements", "Funding", "Doi", "PathPatterns"]
    dataset_description.update({key: value for key, value in metadata_dict.items() if key not in duplicate_keys}
    )

    if output_path is not None:
        save_json(dataset_description, Path(output_path)/'dataset_description.json')

    return dataset_description


def create_participants_tsv(bids_root_dir, **kwargs):
    """
    Creates a participants.tsv file from BIDS directories.

    Parameters:
    - bids_root_dir: Path to the BIDS root directory.
    - output_file: Path where the participants.tsv file will be saved.
    """
    participants_data = []

    # Iterate over each participant directory in the BIDS root directory
    for participant_dir in Path(bids_root_dir).glob('sub-*'):
        participant_id = participant_dir.name

        # Example of extracting participant information
        # This should be adapted based on how participant information is stored in your dataset
        age = "n/a"  # Placeholder for age
        sex = "n/a"  # Placeholder for sex
        modalities = "n/a"  # Placeholder for modalities
        body_parts = "n/a"  # Placeholder for body parts

        # Append the participant's information to the list
        participants_data.append({
            "participant_id": participant_id,
            "age": age,
            "sex": sex,
            "modalities": modalities,
            "body_parts": body_parts
        })

    # Create a DataFrame
    participants_df = pd.DataFrame(participants_data)

    # Save the DataFrame to a TSV file
    participants_df.to_csv('participants.tsv', sep='\t', index=False)
    return participants_df

def create_tsvs(data_path: [Path, str], dataset_info: dict = dict(), radiology_reports_dict: dict = dict() ):

    """
    Function to create the necessary participants tsv file for bids compliant.
    # Code adapted from https://github.com/BIMCV-CSUSP/MIDS/blob/main/xnat2mids/mids_conversion.py

    Parameters
    ----------
    data_path: Path
        path to the data
    info_filepath: Path
        path to the info file

    radiology_reports_dict: dict (optional= dict())
        dictionary with the radiology reports

    Returns
    -------
    None
    """
    data_path = Path(data_path)

    participants_information= []
    for subject_path in sorted(data_path.glob('sub-*/')):
        # print(subject_path.name)
        if not (subject_path.is_dir()):
            continue

        subject = subject_path.parts[-1]
        try:
            subject_id =  re.search(r'\d+', subject).group() # re.findall( r'\d{2,}', subject.split("-")[-1])
        except:
            subject_id =  subject.split("-")[-1]
        sessions_information = []
        modalities = []
        body_parts = []
        patient_birthday = None
        patient_ages = list([])
        patient_sex = None
        adquisition_date_time = None
        for session_path in Path(subject_path).glob('ses-*/'):
            # if not session_path.match("ses-*"): continue
            session = session_path.parts[-1]
            session_id = session.split("-")[-1]

            report = radiology_reports_dict.get(int(subject_id), {}).get("report", "n/a")
            report = re.sub(r'[^\w\s\d\t]|[\n]', '', report) if report != "n/a" else "n/a"
            scans_information = []

            for json_pathfile in session_path.glob('**/*.json'):
                note_path = json_pathfile.parent.joinpath(json_pathfile.stem + ".txt")
                note = ""
                if note_path.exists():
                    with note_path.open('r') as file_:
                        note = file_.read()
                    note_path.unlink()
                    if not note:
                        logging.info(f"empty note : {note_path}")                        # raise FileNotFoundError
                else:
                    logging.info(f"notes not found for {subject}-{session}")

                chunk_search = chunk_pattern.search(json_pathfile.stem)
                if chunk_search:
                    list_nifties = json_pathfile.parent.glob(
                        chunk_pattern.sub(
                            "*",
                            json_pathfile.stem
                        ) + "*"
                    )
                else:
                    list_nifties = json_pathfile.parent.glob(
                        json_pathfile.stem + "*"
                    )

                list_nifties = [f for f in list_nifties if ".nii" in f.suffixes]
                logging.info(json_pathfile)
                json_file = load_json(json_pathfile)
                #print(json_file)
                pseudo_id = subject #json_file.get("PatientID", {"Value": []}).get("Value"))
                modality = json_file.get("Modality", {}).get("Value", ["n/a"])[0]

                modalities.append(modality) #'[participants_keys[0]])

                body_parts.append(
                    json_file.get("BodyPartExamined", {}).get("Value", dataset_info.get("BodyPartExamined", ["n/a"]))[0] )

                patient_birthday = json_file.get("PatientBirthDate", { }).get("Value", [""])[0]

                try:
                    patient_birthday = datetime.fromisoformat(patient_birthday) if patient_birthday else "n/a"
                except ValueError:
                    patient_birthday = datetime.fromisoformat(f"{patient_birthday[0:4]}-{patient_birthday[4:6]}-{patient_birthday[6:8]}") if patient_birthday else "n/a"
                patient_sex = json_file.get("PatientSex", {"Value": ["n/a"]}).get("Value", ["n/a"])[0]

                acquisition_date = json_file.get("AcquisitionDate",{}).get("Value", ["n/a"])[0]
                if acquisition_date == "n/a" or acquisition_date == "":
                    acquisition_date = json_file.get("StudyDate",{}).get("Value", [""])[0]
                    acquisition_date = datetime.strptime(acquisition_date, "%Y%m%d%H%M%S.%f") if acquisition_date else  "n/a"

                age = json_file.get("PatientAge", {}).get("Value", ["n/a"])[0]

                if patient_birthday != "n/a" and acquisition_date != "n/a":
                    age = int((acquisition_date - patient_birthday).days / (365.25))
                #strip the numeric string   from the age
                if age != "n/a":
                    age = int( re.sub(r'\D', '', age)) #if age != "n/a" else int(age)
                    patient_ages.append(age)

                if modality == 'MR':
                    for nifti in list_nifties:
                        values = [json_file.get(key, {}).get('Value', ['n/a']) for key in scans_header_mr[2:]]
                        scans_information.append({
                            key: value
                            for key, value in zip(
                                scans_header_mr,
                                [
                                    str(nifti.relative_to(session_path)),
                                    body_parts[-1],
                                    # todo: find a way to unpack the list of values
                                    *[item[0] if len(item) == 1 else item for item in values],
                                    #*[json_file.get(key, {}).get('Value', ['n/a'])[:2] for key in scans_header_mr[2:]],
                                    note
                                ]
                            )
                        })
                if modality in ["OP", "SC", "XC", "OT"]:
                    for nifti in list_nifties:
                        scans_information.append({
                            key: value
                            for key, value in zip(
                                scans_header_op,
                                [
                                    str(nifti.relative_to(session_path)),
                                    body_parts[-1],
                                    *[json_file.get(key, {}).get('Value', ['n/a'])[0] for key in scans_header_op[2:-1]],
                                    note
                                ]
                            )
                        })
                if modality in ["SM"]:
                    for nifti in sorted(list_nifties):
                        scans_information.append({
                            key: value
                            for key, value in zip(
                                scans_header_micr,
                                [
                                    str(nifti.relative_to(session_path)),
                                    body_parts[-1],
                                    *[json_file.get(key_, "n/a") for key_ in scans_header_micr[2:]],
                                    note
                                ]
                            )

                        })

            patient_ages = sorted(list(set(patient_ages)))
            modalities = sorted(list(set(modalities)))
            body_parts = sorted(list(set(body_parts)))
            if Path(json_pathfile).exists():  # write
                study_uid = json_file.get('StudyInstanceUID', {}).get('Value', ['n/a'])[0]
            else:
                study_uid = "n/a"

            sessions_information.append({
                k: v
                for k, v in zip(
                    session_header,
                    [session, study_uid, acquisition_date.isoformat() if acquisition_date != "n/a" else "n/a" , report]
                )

            })
            scans_df = pd.DataFrame.from_dict(scans_information)
            scans_df = scans_df.replace('n/a', np.nan).dropna(axis=1, how='all')

            scans_df.replace( np.nan,'n/a').to_csv(
                session_path.joinpath(f"{subject}_{session}_scans.tsv"), sep="\t", index=False
            )
            save_json({ k:v for k,v in SCANS_MR_FIELDS.items() if k in scans_df.columns},
                      filename=f"{subject}_{session}_scans.json", path=session_path)

        sessions_df = pd.DataFrame.from_dict(sessions_information)#.replace('n/a', np.nan).dropna(axis=1, how='all')
        sessions_df.replace( np.nan,'n/a').to_csv(
            subject_path.joinpath(f"{subject}_sessions.tsv"), sep="\t", index=False
        )
        save_json(SESSION_FIELDS,
                  filename=f"{subject}_sessions.json", path=subject_path)

        pid_info = {
            k: v
            for k, v in zip(
                participants_header,
                [[subject], patient_ages, [patient_sex],  modalities, [','.join([f"{b}" for b in body_parts if  b])]]
            )
        }
        #print(f"The body parts are: {body_parts}")
        participants_information.append({k: (v[0] if v  else "n/a") for k, v in pid_info.items()})

    participants_df = pd.DataFrame.from_dict(participants_information)
    participants_df.to_csv(
        data_path.joinpath("participants.tsv"), sep="\t", index=False
    )

    save_json(PARTICIPANTS_FIELDS,
              filename = "participants.json", path = data_path)

    return participants_information


def  extract_nifti_metadata(file_path, body_part = 'LSPINE', modality = 'MR'):
    tags = {
        "Modality": {
            "tag": "00080060",
            "Value": [
                f"{modality}"
            ],
            "vr": "CS"
        },
        "SeriesDescription": {
            "tag": "0008103E",
            "Value": [
            ],
            "vr": "LO"
        },
        "BodyPartExamined": {
            "tag": "00180015",
            "Value": [
                " "
            ],
        "vr": "CS"
    },
    "PixelSpacing": {
        "tag": "00280030",
        "Value": [
            1.0,
            1.0
        ],
        "vr": "DS"
    },
    "SliceThickness": {
        "tag": "00180050",
        "Value": [
            3
        ],
        "vr": "DS"
    },
    "ImageOrientationPatient": {
        "tag": "00200037",
        "Value": [
            1,
            0,
            0,
            0,
            1,
            0
        ],
        "vr": "DS"},
    "SeriesDescription": {
        "tag": "0008103E",
        "Value": [
            ""
        ],
        "vr": "LO"},
    }
    try:
        tags = create_metadata_dict(body_part, file_path, modality, tags)
    except Exception as e:
        sitk.WriteImage( sitk.ReadImage(str(file_path)) , str(file_path) )
        logging.info(f"Image saved as {file_path}")
        try:
            tags = create_metadata_dict(body_part, file_path, modality, tags)
        except Exception as e:
            logging.error(f"Error extracting metadata from {file_path}: {e}")
            return tags
    return tags


def create_metadata_dict(body_part, file_path, modality, tags):
    # Load the NIfTI file
    nifti_image = nib.load(file_path)
    # Access the header of the NIfTI file
    header_dict = dict(nifti_image.header)
    # Extract the metadata from the header
    tags["Modality"]["Value"] = [modality]
    tags["SeriesDescription"]["Value"] = [(header_dict.get("descrip", "").tobytes().decode('utf-8').strip('\x00'))]
    tags["BodyPartExamined"]["Value"] = [body_part] if body_part else [""]
    tags["PixelSpacing"]["Value"] = header_dict.get("pixdim", [1.0, 1.0, 1.0])[1:3].tolist()
    tags["SliceThickness"]["Value"] = [header_dict.get("pixdim", [1.0, 1.0, 1.0])[3].tolist()]
    tags["ImageOrientationPatient"]["Value"] = list(header_dict.get("srow_x", [1, 0, 0])[:3].tolist()) + list(
        header_dict.get("srow_y", [0, 1, 0])[:3].tolist())
    tags["SeriesDescription"]["Value"] = [header_dict.get("descrip", "").tobytes().decode('utf-8').strip('\x00')]
    return tags



def create_mids_filename(subject_id, session_id, metadata_lists =  {'BodyPartExamined': ['LSPINE'],
                                                                          'Dimension': [''],
                                                                          'ImagePlane': ['sag'],
                                                                          'ModalityType': ['T2w']}, **kwargs
                         ): # Default metadata values

    """
    Creates the BIDS-compatible filename for a given subject, session, body part, acquisition, run, and image plane.

    Parameters:
    - subject_id: The subject ID as a string.
    """
    body_part = kwargs.get('BodyPartExamined', metadata_lists.get('BodyPartExamined', [''])[0]) .lower()
    acquisition = kwargs.get('Acquisition', metadata_lists.get('Acquisition', [''])[0])
    dimension = kwargs.get('Dimension', metadata_lists.get('Dimension', [''])[0])
    acquisition = f'{dimension}-{acquisition}' if dimension else acquisition
    acquisition = acquisition[1:] if acquisition.startswith('-') else acquisition
    image_plane = kwargs.get('ImagePlane', metadata_lists.get('ImagePlane', [''])[0]).lower()
    modality_type = kwargs.get('ModalityType', metadata_lists.get('ModalityType', [''])[0])

    series_number = 1
    filename = f"sub-{subject_id}_ses-{session_id:02d}_bp-{body_part}_acq-{acquisition}_run-{series_number:02d}_vp-{image_plane[:3]}_{modality_type}.nii.gz"
    return filename

def segmentation_mids_filename(subject_id, session_id,  series_number = 1, **kwargs ): # Default metadata values

    """
    Creates the BIDS-compatible filename for a given subject, session, body part, acquisition, run, and image plane.

    Parameters:
    - subject_id: The subject ID as a string.
    """
    filename = f"sub-{subject_id}_ses-{session_id:02d}"
    if 'BodyPartExamined' in kwargs:
        filename += f"_bp-{kwargs['BodyPartExamined'].lower()}"
    if 'Acquisition' in kwargs:
        filename += f"_acq-{kwargs['Acquisition']}"
    if 'Description' in kwargs:
        filename += f"_desc-{kwargs['Description']}"
    if 'Space' in kwargs:
        filename += f"_space-{kwargs['Space']}"
    filename += f"_run-{series_number:02d}"
    if 'ImagePlane' in kwargs:
        filename += f"_vp-{kwargs['ImagePlane'][:3]}"
    if 'ModalityType' in kwargs:
        filename += f"_mod-{kwargs['ModalityType']}"

    filename += "_dseg.nii.gz"

    return filename


def convert_dicom_to_nifti(dicomdir: [Path | str], bidsdir: [Path | str], pidp: str = "ID") -> None:
    """
    Convert DICOM files in a directory to NIFTI format and organize them in a BIDS directory.

    Parameters:
    ----------
    dicomdir: str
        Path to the directory containing the DICOM files.
    bidsdir: str
        Path to the BIDS directory where the NIFTI files will be stored.
    pidp: str
      Prefix for the participant ID.

    Returns:
    -------
        None

    This function converts DICOM files in a directory to NIFTI format using the dcm2niix tool.
    The converted NIFTI files are organized in a BIDS directory structure. The function
    iterates over each subject directory in the DICOM directory and for each subject, it
    creates a BIDS session directory. Within each session directory, it converts the DICOM
    files to NIFTI format and copies the corresponding JSON metadata file. The function
    handles multiple sessions per subject and creates separate session directories for each
    """
    dicomdir_path = Path(dicomdir)
    bidsdir_path = Path(bidsdir)
    tmpdir_path = bidsdir_path / 'derivatives' / 'nifti'
    tmpdir_path.mkdir(parents=True, exist_ok=True)
    for pdir in sorted(dicomdir_path.glob('*')):
        if pdir.is_dir():
            id =extract_number(pdir.name)
            pid = f"{pidp}{int(id):03d}"
            print(f" ------------------------------- ")
            print(f"Processing subject ID {id} into {pid}")
            print(f" ------------------------------- ")

            ses = 1
            for sesid in pdir.glob('*'):
                ses_dir = tmpdir_path / f'sub-{pid}' / f'ses-{ses:02d}'
                ses_dir.mkdir(parents=True, exist_ok=True)

                for sid in sesid.glob('*'):
                    (ses_dir / sid.name).mkdir(parents=True, exist_ok=True)
                    if sid.is_dir():

                        # Run dcm2niix and capture its output
                        command = [
                            'dcm2niix', '-b', 'n', '-z', 'y', '-m', 'y',
                            '-f', f'sub-{pid}_ses-{ses}_%c',
                            '-o', f'{(ses_dir/sid.name).as_posix()}',
                            str(sid)
                        ]

                        result = subprocess.run(command, capture_output=True, text=True)
                        output = result.stdout

                        # Check if the conversion was successful
                        if result.returncode != 0:
                            logging.error(f"Error converting DICOM files to NIFTI format: {result.stderr}")
                            continue

                        # Short only the MR files
                        for f in (ses_dir/sid.name).glob('*mod-MR-*.nii.gz'):

                            # Retrieve the modality as the last part of the file segment splited by '_' before the extension
                            modality =  f.stem.split('.')[0].split('_')[-1].split('-')[-1]
                            for m, mtype in MODALITIES.items():
                                if modality in mtype:
                                    fname = f.name.replace('mod-MR-', f'')
                                    if 'Eq_' in fname:
                                        # Check if the file name matches the Equidistant resampled pattern
                                        fname = re.sub( r'_Eq_[1-9]', '', fname).replace(r'_run', '_desc-equidistant_run')

                                    fname = re.sub(r'_Eq.*', '.nii.gz', fname)
                                    mod_dir =  bidsdir_path / f'sub-{pid}' / f'ses-{ses:02d}' / f'mr-{m}'
                                    mod_dir.mkdir(parents=True, exist_ok=True)

                                    f.replace(mod_dir /fname)
                                    # Copy the extracted metadata from the dicom directory
                                    json_source = sid / f"{sid.name}.json"
                                    if json_source.exists():
                                        #json_source.replace(mod_dir / f"{Path(Path(fname).stem).with_suffix('.json')}")
                                        shutil.copy2(json_source, mod_dir / f"{Path(Path(fname).stem).with_suffix('.json')}")
                ses += 1
    # Cleanup
    subprocess.run(['rm', '-r', '-f', str(tmpdir_path)])
