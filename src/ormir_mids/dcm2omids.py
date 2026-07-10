#!/usr/bin/env python3
import copy
import pprint
import re
import json
import os
import sys

from voxel import MedicalVolume

from .converters import RootConverter
from .utils.headers import concatenate_volumes_3d, group, get_raw_tag_value, force_change_header_value
from .utils.io import load_dicom, save_omids, load_dicom_with_subfolders
import pathlib

import argparse

def parse_patient_name(patient_name):
    try:
        return patient_name['Alphabetic']
    except KeyError:
        return str(patient_name)

def is_valid_dicom_uid(uid: str) -> bool:
    # Pattern combines the component rules and length restriction
    pattern = r"^(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){0,63}$(?<=^.{1,64}$)"
    return bool(re.match(pattern, uid))

def parse_list_expression(list_expression):
    """
    Parse a list expression in the format [start:increment:end]. If the end is prefixed with 'n', then this number
    of values are generated. Note: end is included.

    Examples:
        "[1:2:11]" -> [1, 3, 5, 7, 9, 11]
        "[1:2:n3]" -> [1, 3, 5]
        "[1,2,3]" -> [1, 2, 3]

    Args:
        list_expression: a string

    Returns:
        a list of integers or floats or strings (UIDs)
    """
    # Check if this is a comma-separated list
    if ',' in list_expression:
        m = re.match(r'\[\s*([^\]]+)\s*\]', list_expression)
        if m is not None:
            values_str = m.group(1).split(',')
            values = []
            for val in values_str:
                val = val.strip()
                # Try to parse as UID
                if is_valid_dicom_uid(val):
                    values.append(val)
                    continue
                # Try to parse as int first, then float
                try:
                    values.append(int(val))
                except ValueError:
                    try:
                        values.append(float(val))
                    except ValueError:
                        raise ValueError(f'Invalid value in list expression: {val}')
            return values
        else:
            raise ValueError('Invalid list expression')

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

def get_volume_matcher(config_expression: str, inputDir = ''):
    """
    Returns a function that matches a volume against an expression

    Args:
        config_expression: an expression in the series_config.json file:
            - a path
            - a series number
            - a series UID
            - a list expression of paths, numbers, UIDs
            - a regular expression

    Returns:
        matcher(MedicalVolume): a function that accepts a MedicalVolume and returns true if it matches

    """
    config_expression = config_expression.strip()

    def _get_relevant_tags(med_volume: MedicalVolume):
        series_number = get_raw_tag_value(med_volume, '00200011')[0]
        series_uid = get_raw_tag_value(med_volume, '0020000E')[0]
        series_description = get_raw_tag_value(med_volume, '0008103E')[0]
        return series_number, series_uid, series_description
    try:
        int_value = int(config_expression)
        # this is a simple integer
        def integerMatcher(v: MedicalVolume):
            series_number, _, _ = _get_relevant_tags(v)
            return int_value == series_number
        return integerMatcher
    except ValueError:
        pass # continue if it's not integer
    if is_valid_dicom_uid(config_expression):
        # single expression
        def uidMatcher(v: MedicalVolume):
            _, series_uid, _ = _get_relevant_tags(v)
            return series_uid == config_expression
        return uidMatcher
    # not a valid UID
    if config_expression.startswith('['):
        # this is a list expression
        value_list = parse_list_expression(config_expression)
        # this can be a list of UIDs, paths, or numbers
        def list_expression_matcher(v: MedicalVolume):
            series_number, series_uid, _ = _get_relevant_tags(v)
            med_path = os.path.abspath(v.path)
            for value in value_list:
                if isinstance(value, int):
                    if series_number == value:
                        return True
                    continue # if it's an integer, and not a match, continue
                if is_valid_dicom_uid(value):
                    if series_uid == value:
                        return True
                    continue # same as above. If it's a UID, and not a match, continue
                target_path = os.path.abspath(os.path.join(inputDir, str(value)))
                if target_path == med_path:
                    return True
            return False # if nothing matches, return false
        return list_expression_matcher
    if config_expression.startswith('/'):
        # regular expression. It is defined as '/expression/'
        expr = re.compile(config_expression.strip('/')) # remove initial and final /
        def regexp_matcher(v: MedicalVolume):
            _, _, series_description = _get_relevant_tags(v)
            return bool(expr.match(series_description))
        return regexp_matcher
    raise ValueError('Invalid expression')

def convert_dicom_to_ormirmids(input_folder, output_folder, anonymize='anon', recursive=True, session='', series_number=False, save_patient_json=True, save_extra_json=True):
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
        med_volume_list = load_dicom(inputDir)

    print("Data loaded")

    multiseries_config = None
    multiseries_volumes = {}
    multiseries_uids = {}
    raw_overrides = {}
    manual_converters = []
    data_info = {}

    if os.path.exists(os.path.join(inputDir, 'series_config.json')):
        with open(os.path.join(inputDir, 'series_config.json')) as json_file:
            multiseries_config = json.load(json_file)
            data_info = copy.deepcopy(multiseries_config)  # this is the output json structure
            # that also contains the initial overrides and series config
            if 'overrides' in multiseries_config:
                raw_overrides = multiseries_config['overrides']
                del multiseries_config['overrides']
            if 'manual_converters' in multiseries_config:
                manual_converters = multiseries_config['manual_converters']
                del multiseries_config['manual_converters']
        print("multiseries config loaded")

    data_info['manual_converters'] = [] # reset the manual converters. It will anyway be (re)created


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
        try:
            series_number_list = [int(series_number)]
        except ValueError:
            # series number is not an int
            if isinstance(series_number, str):
                if series_number.startswith('['):
                    try:
                        series_number_list = parse_list_expression(series_number)
                    except ValueError:
                        print("Error parsing series number in overrides")
                        continue
                else:
                    if is_valid_dicom_uid(series_number):
                        series_number_list = [series_number] # this is a uid
                    else:
                        try:
                            # check if this is a reference to a multiseries config
                            series_number_list = multiseries_config[series_number]
                        except KeyError:
                            print("Error parsing series number in overrides: not a UID, integer, list expression, or multiseries config reference:", series_number)
                            continue
            else:
                print("Invalid entry for override series config:", series_number)
                continue


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
                # check if there are different values for every element in the series_number_list
                if isinstance(value, list) and len(value) == len(series_number_list):
                    override_dict_for_series[key] = value[series_index]
                else:
                    override_dict_for_series[key] = value
            overrides[series_number] = override_dict_for_series

    print('Overrides', overrides)

    multiseries_finished = None

    for med_volume in med_volume_list:
        series_number = get_raw_tag_value(med_volume, '00200011')[0]
        series_uid = get_raw_tag_value(med_volume, '0020000E')[0]
        # overrides can be saved with series number or uid as indices
        if series_number in overrides:
            for key, value in overrides[series_number].items():
                print("Applying override for series", series_number, ":", key, "=", value)
                force_change_header_value(med_volume, 'omids', key, value)
                # med_volume.omids_header[key] = value
        if series_uid in overrides:
            for key, value in overrides[series_uid].items():
                print("Applying override for series", series_uid, ":", key, "=", value)
                force_change_header_value(med_volume, 'omids', key, value)
                # med_volume.omids_header[key] = value

    def convert_recursive(converter_class, med_volume):
        #print('Checking converter', converter_class.get_name())
        compatible_dataset = False

        try:
            compatible_dataset = converter_class.is_dataset_compatible(med_volume)
        except Exception as e:
            pass

        if not compatible_dataset:
            return False

        converted = False

        # if the converter_class is compatible, check its children
        # try converting the dataset with each child converter as the same dataset may be compatible with multiple converters
        for child_converter in converter_class.get_children():
            try:
                converted = convert_recursive(child_converter, med_volume) or converted
            except Exception as e:
                pass

        # After all the children, try the base class too.
        if multiseries_part == converter_class.is_multiseries():
            try:
                converted_volume = converter_class.convert_dataset(med_volume)
            except Exception as e:
                print(f'Error converting volume with {converter_class.get_name()}: {e}')
                converted_volume = None
            if converted_volume is None:
                # This class cannot convert datasets, it's just a dependency class
                return converted
            if ANON_NAME:
                patient_name = ANON_NAME
            else:
                patient_name = parse_patient_name(med_volume.patient_header['PatientName'])
            if outputDir:
                output_path = pathlib.Path(outputDir) / os.path.dirname(converter_class.get_file_path(patient_name, session))
                output_path.mkdir(parents=True, exist_ok=True)
            if multiseries_part:
                if multiseries_finished is not None:
                    # a multiseries is finished, we can concatenate
                    concat_volume_4d = concatenate_volumes_3d(multiseries_volumes[series_group_name])
                    converted_multiseries_volume = group(concat_volume_4d, converter_class.multiseries_concat_tag())

                    series_prefix = ''
                    if ADD_SERIES_NUMBER:
                        first_series = min(
                            [get_raw_tag_value(x, '00200011')[0] for x in multiseries_volumes[series_group_name]])
                        series_prefix = f'{first_series:03d}_'
                    if outputDir:
                        save_omids(
                            str(output_path / (series_prefix + converter_class.get_file_name(patient_name, session))) + '.nii.gz',
                            converted_multiseries_volume, save_patient_json, save_extra_json)
                    print('Volume', med_volume.path, converted_multiseries_volume.shape, 'saved with', converter_class.get_name(), 'using multiseries concatenation')
                    if getattr(med_volume, 'compatible_converters', None) is None:
                        setattr(med_volume, 'compatible_converters', [])
                    med_volume.compatible_converters.append(converter_class)
                    setattr(med_volume, 'multiseries_uids', multiseries_uids[series_group_name])
                    return True # we successfully converted the multiseries volume

            series_prefix = ''
            if ADD_SERIES_NUMBER:
                series_prefix = f'{get_raw_tag_value(med_volume, "00200011")[0]:03d}_'
            if outputDir:
                save_omids(str(output_path / (series_prefix + converter_class.get_file_name(patient_name, session))) + '.nii.gz',
                       converted_volume, save_patient_json, save_extra_json)
            print('Volume', med_volume.volume.shape, med_volume.path, 'saved with', converter_class.get_name())
            if getattr(med_volume, 'compatible_converters', None) is None:
                setattr(med_volume, 'compatible_converters', [])
            med_volume.compatible_converters.append(converter_class)
            return True # we successfully converted the volume

        return converted # return if any child converted the volume

    data_info = []

    for med_volume in med_volume_list:
        multiseries_part = False
        if multiseries_config:
            series_number = get_raw_tag_value(med_volume, '00200011')[0]
            series_uid = get_raw_tag_value(med_volume, '0020000E')[0]
            med_path = os.path.abspath(med_volume.path)


            for series_group_name, series_list in multiseries_config.items():
                # check if this series is part of a group
                if series_number in series_list or \
                        med_path in [os.path.abspath(os.path.join(inputDir, str(x))) for x in series_list] or \
                        series_uid in series_list:
                    if series_group_name not in multiseries_volumes:
                        multiseries_volumes[series_group_name] = []
                    multiseries_volumes[series_group_name].append(med_volume)
                    if series_group_name not in multiseries_uids:
                        multiseries_uids[series_group_name] = []
                    multiseries_uids[series_group_name].append(series_uid)
                    multiseries_part = True
                    print('Multiseries part:', series_group_name)
                    if len(multiseries_volumes[series_group_name]) == len(series_list):
                        multiseries_finished = series_group_name
                        print('Multiseries finished:', series_group_name)
                    else:
                        multiseries_finished = None
                    break # don't search for other groups

        if convert_recursive(RootConverter, med_volume):
            print("Dataset converted successfully")
            info_object = {
                'SeriesUID': get_raw_tag_value(med_volume, '0020000E')[0],
                'SeriesDescription': get_raw_tag_value(med_volume, '0008103E')[0],
                'Converters': []
            }
            multiseries_uids_for_volume = getattr(med_volume, 'multiseries_uids', None)
            if multiseries_uids_for_volume:
                info_object['SeriesUID'] = multiseries_uids_for_volume
            for converter_class in med_volume.compatible_converters:
                if converter_class is RootConverter:
                    continue
                if not converter_class.get_directory():
                    continue
                converter_object = {
                    'Name': converter_class.get_name(),
                    'Directory': converter_class.get_directory(),
                    'Suffix': converter_class.get_suffix()
                }
                info_object['Converters'].append(converter_object)
            data_info['manual_converters'].append(info_object)
        else:
            print("No compatible converter found for dataset", med_volume.path)
    return data_info


def main():
    parser = argparse.ArgumentParser(description='Convert DICOM to ORMIR-MIDS format')
    parser.add_argument('input_folder', type=str, help='Input folder')
    parser.add_argument('output_folder', type=str, nargs='?', const=None, help='Output folder. Omit to avoid converting')
    parser.add_argument('--anonymize', '-a', const='anon', metavar='pseudo_name', dest='anonymize', type=str, nargs = '?', help='Use the pseudo_name (default: anon) as patient name')
    parser.add_argument('--recursive', '-r', action='store_true', help='Recurse into subfolders')
    parser.add_argument('--series-number', '-s', action='store_true', help='Add series number to file name')
    parser.add_argument('--disable-patient-json', '-p', action='store_true', help='Avoid saving patient json file')
    parser.add_argument('--disable-extra-json', '-e', action='store_true', help='Avoid saving extra json file')
    parser.add_argument('--session', metavar='session_id', type=str, nargs=1,
                        help='Specify the session ID to use (default: none)')
    parser.add_argument('--save-info-json', type=str, nargs=1, help='Save info json file')


    args = parser.parse_args()

    inputDir = args.input_folder
    outputDir = args.output_folder
    ANON_NAME = args.anonymize
    RECURSIVE = args.recursive
    ADD_SERIES_NUMBER = args.series_number
    save_json = args.save_info_json
    if not outputDir and not save_json:
        print("Warning! No output dir specified and no output json. This command will have no effect.")
    if args.session:
        SESSION = args.session[0]
    else:
        SESSION = None
    data_info = convert_dicom_to_ormirmids(inputDir, outputDir, ANON_NAME, RECURSIVE, SESSION, ADD_SERIES_NUMBER, not args.disable_patient_json, not args.disable_extra_json)
    if save_json:
        with open(save_json[0], 'w') as f:
            json.dump(data_info, f, indent=4)

# if __name__ == "__main__":
#     main()