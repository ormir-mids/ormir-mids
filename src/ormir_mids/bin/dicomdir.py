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

import pandas as pd
import pydicom  # pydicom is using the gdcm package for decompression
from pathlib import Path
import argparse
import SimpleITK as sitk
from tqdm import tqdm
import numpy as np
import re
import logging
from pydicom.datadict import keyword_for_tag

from ..mri import CONTRAST_REGEX, modality_approximation, match_mri_modality, search_mri_sequence, \
    acquisiton_dimension
from ..mri.orientation import get_imaging_plane, extract_image_plane_from_description, get_view_plane_short
from ..utils.files import save_json, load_yaml
from ..utils.strings import remove_nonalphanumeric, remove_special_characters

def save_patient_dicomdir(dir_path: Path,
                          output_folder: [str, Path],
                          pid: [str | None] = None,
                          default: dict = { "Modality": "MR",
                                            "BodyPartExamined": "SPINE",
                                            "ProtocolName": "TSE"}):

    """ Function to structure the DICOM files of a patient in a folder.
    Parameters:
    -----------
    dir_path: Path
        The path to the patient folder
    output_folder: str or Path
        The path to the output_mask folder
    pid: str
        The patient if want to keep. If none retrieve from the DICOM series header
    default: dict
        The default values to use if the DICOM series header is missing
        default = { "Modality": "MR",
                    "BodyPartExamined": "SPINE",
                    "ProtocolName": "TSE"}

    Returns
    -------
    series_overview: list
        A list of dictionaries containing the information of the series
    changelog: list
        A list of lists containing the information of the files
    Examples:
    ---------
    changelog = structure_patient_datadir(patient_datadir, PID, source_datafolder, target_datafolder)
    """
    reader = sitk.ImageSeriesReader()
    changelog = []

    print(f'Processing Patient: {dir_path}')

    PID = dir_path.name.replace('-', '') if pid is None else pid.upper()

    for series_dir in np.unique(
            [fp.parent for fp in dir_path.rglob('*') if fp.is_file() and 'loc' not in fp.parent.name]):
        series_description = ""

        for series_id in reader.GetGDCMSeriesIDs(str(series_dir)):
            logging.info(f"Processing Series: {series_id}")
            df0 = reader.GetGDCMSeriesFileNames(str(series_dir), series_id)[0]
            ds0 =  pydicom.read_file(str(df0), force=True)
            try: # Try to get the series information from the dicom metadata
                patientID = remove_nonalphanumeric(ds0.get("PatientID",
                                                              f"{PID}")) if pid is None else pid  # dir_path.name

                studyDate = remove_nonalphanumeric(
                    ds0.get("StudyDate", ds0.get("SeriesDate", ds0.get("AcquisitionDate", " "))))
                modality = ds0.get("Modality",  default.get("Modality", ""))

                body_part = remove_nonalphanumeric(ds0.get("BodyPartExamined", default.get("BodyPartExamined", "")))
                body_part = default.get("BodyPartExamined", "").upper() if not body_part else body_part.upper()


                image_orientation_patient = ds0.get("ImageOrientationPatient", None)

                view_plane = get_imaging_plane(
                    image_orientation_patient) if image_orientation_patient else extract_image_plane_from_description(
                    series_description)

                view_plane = get_view_plane_short(view_plane)

                series_description = ds0.get("SeriesDescription", f"{Path(df0).parent.name}")
                protocol = match_mri_modality(ds0.get('ProtocolName', default.get("ProtocolName", "")))
                protocol = match_mri_modality(remove_special_characters(series_description)) if protocol is None else protocol
                protocol = protocol if protocol is not None else modality_approximation(ds0.get('EchoTime', 0),
                                                                                        ds0.get('RepetitionTime', 0),
                                                                                        ds0.get('InversionTime', 0),
                                                                                        default_sequence="")

                acquisition = ds0.get('MRAcquisitionType', acquisiton_dimension(ds0.get('AcquisitionMatrix', [0, 0, 0, 0])))

                contrast = ""
                if 'LOC' not in protocol and 'CAL' not in protocol:
                    s = search_mri_sequence(ds0.get('SequenceName', ds0.get('ProtocolName', '')),
                                            remove_special_characters(series_description))
                    acquisition = f"{acquisition}-{s}" if s is not None else acquisition

                if re.match(CONTRAST_REGEX, series_description, re.IGNORECASE):
                    contrast = f"_ce-{ds0.get('ContrastBolusAgent', '')}_"
                    protocol = f"{protocol}ce"

                    # ds.SeriesDescription = series_description
                sn = str(ds.get('SeriesNumber', 0)).zfill(2)
                series_classification = f"bp-{body_part}_acq-{acquisition}{contrast}_run-{sn}_vp-{view_plane}_mod-{protocol}"


                series_fps = []
                # Make sure only the series id filepaths are read
                for i, dfp in enumerate(reader.GetGDCMSeriesFileNames(str(series_dir), series_id)):
                    series_fps += [ str(Path(dfp).relative_to(dir_path.parent))]
                    # read the file_metadata
                    ds = pydicom.read_file(str(dfp), force=True)
                    try:
                        ds.PatientID = patientID
                        ds.SeriesDescription = series_description
                        ds.ImageComments = series_classification
                        ds.BodyPartExamined = body_part

                        studyInstanceUID = f"{ds.get('StudyInstanceUID', str(ds.get('SeriesNumber')).zfill(3))}"
                        seriesInstanceUID = f"{ds.get('SeriesInstanceUID', str(ds.get('SeriesNumber', 0)).zfill(3))}"
                        instanceNumberUID = f"{ds.get('SOPInstanceUID', ds.get('SeriesInstanceUID', series_id))}"  # f"{ds.get('SOPInstanceUID', seriesInstanceUID)}.{str(ds.get('InstanceNumber', i)).zfill(4)}"
                        fp = Path( output_folder) / patientID / studyInstanceUID / seriesInstanceUID / f"{instanceNumberUID}.dcm"
                        Path(fp.parent).mkdir(parents=True, exist_ok=True)
                        ds.save_as(f"{fp}")
                        logging.info(f"Saved dicom slice in {fp}")
                        changelog.append([f"{patientID}", f"{studyDate}", seriesInstanceUID, str(dfp), str(fp)])
                    except:
                        continue

                ds0.ImageComments= series_classification
                ds0.BodyPartExamined = body_part
                ds0.PatientID = patientID
                ds0.SeriesDescription =  remove_special_characters(series_description)

                # Save Metadata for the whole series in a json file
                metadata_dict = {
                    keyword_for_tag(tag): {'tag': tag, 'Value': values.get('Value', ['']), 'vr': values.get('vr', '')}
                    for tag, values in ds0.to_json_dict().items()}
                metadata_dict.pop("PixelData")
                metadata_dict["SourceFilepaths"] = series_fps
                #metadata_dict["SeriesInfo"] = series_classification

                studyInstanceUID = f"{ds0.get('StudyInstanceUID', str(ds0.get('SeriesNumber')).zfill(3))}"
                seriesInstanceUID = f"{ds0.get('SeriesInstanceUID', str(ds0.get('SeriesNumber', 0)).zfill(3))}"

                # (Path( output_folder)  / patientID / studyInstanceUID/ seriesInstanceUID).mkdir(parents=True, exist_ok=True)
                save_json(metadata_dict, f"{seriesInstanceUID}.json",
                          Path(output_folder) / patientID / studyInstanceUID / seriesInstanceUID)


            except:
                continue
            logging.info(series_description)

    return changelog


def main(rawdata_folder, output_folder, patient_regex, **kwargs):
    changelog = []
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    patient_fpaths = sorted(Path(rawdata_folder).glob(patient_regex))
    patientUIDs = ["PID"+re.search(r'\d+', p.relative_to(p.parent).as_posix()).group().zfill(3) for p in patient_fpaths  ]

    for i, pf in tqdm(enumerate(patient_fpaths), desc="Processing Files", total=len(patient_fpaths)):
        logs = save_patient_dicomdir(pf, output_folder, patientUIDs[i], default=kwargs)
        changelog += logs

    # Save the changelog
    traceback = pd.DataFrame(changelog, columns=["PID", "StudyDate", "SeriesInstanceUID", "Source", "Target"])
    traceback.to_csv(Path(output_folder) / "changelog.log", index=False, sep="\t")


def args_parser(env_file: str = ".env") -> argparse.Namespace:
    """ Argument parser for the main script """
    # Load the environment variables

    parser = argparse.ArgumentParser(description="Organize Raw Dicom and nested data into DICOMDIR format.")


    parser.add_argument("-d", "--data_path", type=str, help=" foldername of the dataset",
                        default=  "data/")

    parser.add_argument("-dn", "--dataset_name", type=str, help="foldername of the dataset",
                        default= 'DATASET')

    parser.add_argument("-t", "--target_path", type=str, help="Target folder for a processed dataset",
                        default= "output")

    parser.add_argument("-p", "--patient_regex", type=str, help="foldername of the dataset",
                        default="*01_MRI/*/")

    parser.add_argument("-c", "--config", type=str, help="config name", default="data")
    parser.add_argument("-pf", "--params_file", type=str, help="additional params config file", default= "config/params.yaml")

    return parser.parse_args()


if __name__ == '__main__':

    # Set the project target_dir, useful for finding various files
    project_dir = Path(__file__).resolve().parents[1]

    # Loads the arguments
    args = args_parser()

    # Load the image_data directory value both, from the environment variable or args if missing
    data_path = args.data_path if args.data_path  else "data"
    dataset_name = args.dataset_name if args.dataset_name is not None else ' '
    output_dir = args.target_path


    kwargs = load_yaml(args.params_file) if Path(args.params_file).exists() else { "Modality": "MR",
                                                                                        "BodyPartExamined": "SPINE",
                                                                                        "ProtocolName": "TSE"}
    main(Path(data_path) / dataset_name, output_dir, args.patient_regex, **kwargs)