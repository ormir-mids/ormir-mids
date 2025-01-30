#!/usr/bin/env python3

import json
import os
import sys
from .utils.headers import concatenate_volumes_3d, group
from .utils.io import load_dicom, save_bids, load_dicom_with_subfolders
from .converters import converter_list
import pathlib

import argparse


def convert_dicom_to_ormirmids(input_folder, output_folder, anonymize='anon', recursive=True):
    """
    Convert DICOM to ORMIR-MIDS format.
    
    Parameters:
    - input_folder (str): Path to the input folder with DICOM files.
    - output_folder (str): Path to the output folder where results will be saved.
    - anonymize (str): Pseudonym for patient name (default: 'anon').
    - recursive (bool): Whether to recurse into subfolders (default: True).
    """
    
    inputDir = input_folder
    outputDir = output_folder
    ANON_NAME = anonymize
    RECURSIVE = recursive
    multiseries_config = None
    multiseries_flag = False
    concat_flag = False
    concat_list = []

    if RECURSIVE:
        med_volume_list = load_dicom_with_subfolders(inputDir)
    else:
        med_volume_list = [load_dicom(inputDir)]

    multiseries_config = None
    multiseries_volumes = {}

    if os.path.exists(os.path.join(inputDir, 'series_config.json')):
        with open(os.path.join(inputDir, 'series_config.json')) as json_file:
            multiseries_config = json.load(json_file)
        print("multiseries config loaded")

    multiseries_finished = None

    for med_volume in med_volume_list:
        multiseries_part = False
        if multiseries_config:
            h = med_volume.headers().ravel()[0]
            med_path = os.path.abspath(med_volume.path)
            for series_group_name, series_list in multiseries_config.items():
                # check if this series is part of a group
                if h.SeriesNumber in series_list or \
                        med_path in [os.path.abspath(os.path.join(inputDir, str(x))) for x in series_list]:
                    if series_group_name not in multiseries_volumes:
                        multiseries_volumes[series_group_name] = []
                    multiseries_volumes[series_group_name].append(med_volume)
                    multiseries_part = True
                    print('Multiseries part:', series_group_name)
                    if len(multiseries_volumes[series_group_name]) == len(series_list):
                        multiseries_finished = series_group_name
                        print('Multiseries finished:', series_group_name)
                    else:
                        multiseries_finished = None
                    break # don't search for other groups
        for converter_class in converter_list:
            if multiseries_part == converter_class.is_multiseries() and \
                    converter_class.is_dataset_compatible(med_volume):
                print('Volume compatible with', converter_class.get_name())
                output_path = pathlib.Path(outputDir) / converter_class.get_directory()
                output_path.mkdir(parents=True, exist_ok=True)
                converted_volume = converter_class.convert_dataset(med_volume)
                if ANON_NAME:
                    patient_name = ANON_NAME
                else:
                    patient_name = med_volume.patient_header['PatientName']
                if multiseries_part:
                    if multiseries_finished is not None:
                        # a multiseries is finished, we can concatenate
                        concat_volume_4d = concatenate_volumes_3d(multiseries_volumes[series_group_name])
                        converted_multiseries_volume = group(concat_volume_4d, converter_class.multiseries_concat_tag())
                        save_bids(str(output_path / converter_class.get_file_name(patient_name)) + '.nii.gz',
                                  converted_multiseries_volume)
                        print('Volume saved')
                    continue
                save_bids(str(output_path / converter_class.get_file_name(patient_name)) + '.nii.gz', converted_volume)
                print('Volume saved')




def main():
    parser = argparse.ArgumentParser(description='Convert DICOM to ORMIR-MIDS format')
    parser.add_argument('input_folder', type=str, help='Input folder')
    parser.add_argument('output_folder', type=str, help='Output folder')
    parser.add_argument('--anonymize', '-a', const='anon', metavar='pseudo_name', dest='anonymize', type=str, nargs = '?', help='Use the pseudo_name (default: anon) as patient name')
    parser.add_argument('--recursive', '-r', action='store_true', help='Recurse into subfolders')

    args = parser.parse_args()

    inputDir = args.input_folder
    outputDir = args.output_folder
    ANON_NAME = args.anonymize
    RECURSIVE = args.recursive
    convert_dicom_to_ormirmids(inputDir, outputDir, ANON_NAME, RECURSIVE)


# if __name__ == "__main__":
#     main()