#!/usr/bin/env python3
import re
import json
import os
import sys
from .utils.headers import concatenate_volumes_3d, group, get_raw_tag_value
from .utils.io import load_dicom, save_omids, load_dicom_with_subfolders
from .converters import converter_list
import pathlib

import argparse

def parse_list_expression(list_expression):
    """
    Parse a list expression in the format [start:increment:end]. If the end is prefixed with 'n', then this number
    of values are generated. Note: end is included.

    Examples:
        [1:2:11] -> [1, 3, 5, 7, 9, 11]
        [1:2:n3] -> [1, 3, 5]

    Args:
        list_expression: a string

    Returns:
        a list of integers or floats
    """
    # this is an integer expression
    m = re.match(r'\[\s*(\d+)\s*:\s*(\d+)\s*:\s*([nN]?\d+)\s*]', list_expression)
    if m is not None:
        start = int(m.group(1))
        step = int(m.group(2))
        if m.group(3).lower().startswith('n'):
            end = start + (int(m.group(3)[1:]) - 1) * step
        else:
            end = int(m.group(3))
        return list(range(start, end + 1, step))

    # this is a float expression
    m = re.match(r'\[\s*(\d*\.?\d+)\s*:\s*(\d*\.?\d+)\s*:\s*([nN]?\d*\.?\d+)\s*]', list_expression)
    if m is None:
        raise ValueError('Invalid list expression')
    start = float(m.group(1))
    step = float(m.group(2))
    if m.group(3).lower().startswith('n'):
        n_values = int(m.group(3)[1:])
    else:
        n_values = int((float(m.group(3))-start)/step) + 1
    return [start + i * step for i in range(n_values)]



def convert_dicom_to_ormirmids(input_folder, output_folder, anonymize='anon', recursive=True, series_number=False, save_patient_json=True, save_extra_json=True):
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
    ADD_SERIES_NUMBER = series_number
    concat_flag = False
    concat_list = []

    if RECURSIVE:
        med_volume_list = load_dicom_with_subfolders(inputDir)
    else:
        med_volume_list = [load_dicom(inputDir)]

    print("Data loaded")

    multiseries_config = None
    multiseries_volumes = {}
    raw_overrides = {}

    if os.path.exists(os.path.join(inputDir, 'series_config.json')):
        with open(os.path.join(inputDir, 'series_config.json')) as json_file:
            multiseries_config = json.load(json_file)
            if 'overrides' in multiseries_config:
                raw_overrides = multiseries_config['overrides']
                del multiseries_config['overrides']
        print("multiseries config loaded")

    if multiseries_config:
        # parse multiseries config
        new_multiseries_config = {}
        for series_group_name, series_list in multiseries_config.items():
            if not isinstance(series_list, list):
                try:
                    series_list = parse_list_expression(series_list)
                except ValueError:
                    print("Error parsing multiseries config for group", series_group_name)
                    continue
                new_multiseries_config[series_group_name] = series_list
                print("Multiseries config for group", series_group_name, ":", series_list)
            else:
                new_multiseries_config[series_group_name] = series_list

        multiseries_config = new_multiseries_config

    # parse overrides
    overrides = {}
    for series_number, override_dict in raw_overrides.items():
        if series_number.startswith('['):
            try:
                series_number_list = parse_list_expression(series_number)
            except ValueError:
                print("Error parsing series number in overrides")
                continue
        else:
            series_number_list = [series_number]

        local_override_dict = {}
        for override_name, override_value in override_dict.items():
            if isinstance(override_value, str):
                try:
                    override_value = parse_list_expression(override_value)
                except ValueError:
                    # it is not a list expression, treat it literally
                    pass
            local_override_dict[override_name] = override_value
        for series_index, series_number in enumerate(series_number_list):
            override_dict_for_series = {}
            for key, value in local_override_dict.items():
                if isinstance(value, list) and len(value) == len(series_number_list):
                    override_dict_for_series[key] = value[series_index]
                else:
                    override_dict_for_series[key] = value
            overrides[series_number] = override_dict_for_series

    print(overrides)




    multiseries_finished = None


    for med_volume in med_volume_list:
        series_number = get_raw_tag_value(med_volume, '00200011')[0]
        if series_number in overrides:
            for key, value in overrides[series_number].items():
                med_volume.omids_header[key] = value

    for med_volume in med_volume_list:
        multiseries_part = False
        if multiseries_config:
            series_number = get_raw_tag_value(med_volume, '00200011')[0]
            med_path = os.path.abspath(med_volume.path)


            for series_group_name, series_list in multiseries_config.items():
                # check if this series is part of a group
                if series_number in series_list or \
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
            try:
                compatible_dataset = converter_class.is_dataset_compatible(med_volume)
            except Exception as e:
                compatible_dataset = False
            if multiseries_part == converter_class.is_multiseries() and compatible_dataset:
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

                        series_prefix = ''
                        if ADD_SERIES_NUMBER:
                            first_series = min([get_raw_tag_value(x, '00200011')[0] for x in multiseries_volumes[series_group_name]])
                            series_prefix = f'{first_series:03d}_'

                        save_omids(str(output_path / (series_prefix + converter_class.get_file_name(patient_name))) + '.nii.gz',
                                  converted_multiseries_volume, save_patient_json, save_extra_json)
                        print('Volume saved')
                    continue
                series_prefix = ''
                if ADD_SERIES_NUMBER:
                    series_prefix = f'{get_raw_tag_value(med_volume, "00200011")[0]:03d}_'
                save_omids(str(output_path / (series_prefix + converter_class.get_file_name(patient_name))) + '.nii.gz', converted_volume, save_patient_json, save_extra_json)
                print('Volume saved')




def main():
    parser = argparse.ArgumentParser(description='Convert DICOM to ORMIR-MIDS format')
    parser.add_argument('input_folder', type=str, help='Input folder')
    parser.add_argument('output_folder', type=str, help='Output folder')
    parser.add_argument('--anonymize', '-a', const='anon', metavar='pseudo_name', dest='anonymize', type=str, nargs = '?', help='Use the pseudo_name (default: anon) as patient name')
    parser.add_argument('--recursive', '-r', action='store_true', help='Recurse into subfolders')
    parser.add_argument('--series-number', '-s', action='store_true', help='Add series number to file name')
    parser.add_argument('--disable-patient-json', '-p', action='store_true', help='Avoid saving patient json file')
    parser.add_argument('--disable-extra-json', '-e', action='store_true', help='Avoid saving extra json file')

    args = parser.parse_args()

    inputDir = args.input_folder
    outputDir = args.output_folder
    ANON_NAME = args.anonymize
    RECURSIVE = args.recursive
    ADD_SERIES_NUMBER = args.series_number
    convert_dicom_to_ormirmids(inputDir, outputDir, ANON_NAME, RECURSIVE, ADD_SERIES_NUMBER, not args.disable_patient_json, not args.disable_extra_json)


# if __name__ == "__main__":
#     main()