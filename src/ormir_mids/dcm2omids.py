#!/usr/bin/env python3

import json
import os
import sys
from .utils.headers import concatenate_volumes_3d, group
from .utils.io import load_dicom, save_bids, load_dicom_with_subfolders
from .converters import converter_list
import pathlib

import argparse

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
    series_config = None
    siemens_megre_flag = False
    concat_flag = False
    concat_list = []

    if RECURSIVE:
        med_volume_list = load_dicom_with_subfolders(inputDir)
    else:
        med_volume_list = [load_dicom(inputDir)]

    if os.path.exists(os.path.join(inputDir + 'series_config.json')):
        siemens_megre_flag = True
        with open(inputDir + 'series_config.json') as json_file:
            series_config = json.load(json_file)

    megre_count = 0
    for med_volume in med_volume_list:
        if siemens_megre_flag and med_volume[0:3] in series_config['series_nos']:
            concat_flag = True
            megre_count += 1
        for converter_class in converter_list:
            if converter_class.is_dataset_compatible(med_volume):
                print('Volume compatible with', converter_class.get_name())
                output_path = pathlib.Path(outputDir) / converter_class.get_directory()
                output_path.mkdir(parents=True, exist_ok=True)
                converted_volume = converter_class.convert_dataset(med_volume)
                if ANON_NAME:
                    patient_name = ANON_NAME
                else:
                    patient_name = med_volume.patient_header['PatientName']
                if concat_flag:
                    concat_list.append(converted_volume)
                    if megre_count == len(series_config['series_nos']):
                        concat_volume_4d = concatenate_volumes_3d(concat_list)
                        converted_megre_volume = group(concat_volume_4d, 'EchoTime')
                        save_bids(str(output_path / converter_class.get_file_name(patient_name)) + '.nii.gz',
                                  converted_megre_volume)
                        print('Volume saved')
                        continue
                    continue
                save_bids(str(output_path / converter_class.get_file_name(patient_name)) + '.nii.gz', converted_volume)
                print('Volume saved')


