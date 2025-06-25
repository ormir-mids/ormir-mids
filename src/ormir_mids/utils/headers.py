import copy
import itertools
import operator
import sys
from collections import OrderedDict

import numpy as np
import pydicom.dataset
from pydicom.uid import generate_uid

from ..config.tag_definitions import defined_tags, patient_tags
from .OMidsMedVolume import OMidsMedVolume as MedicalVolume
from .OMidsMedVolume import copy_headers

from itertools import groupby

def _list_all_equal(iterable):
    """ Checks if all elements in a list are equal"""
    g = groupby(iterable)
    return next(g, True) and not next(g, False)

def _get_value_tag(element):
    """ gets the name of the entry that contains the value of a tag in a generic way

    Parameters:
        element (dict): the dicom tag element

    Returns:
        str: The name of the value tag
    """
    value_tag = 'Value'
    if 'InlineBinary' in element: value_tag = 'InlineBinary'
    if 'BulkDataURI' in element: value_tag = 'BulkDataURI'
    if 'Alphabetic' in element: value_tag = 'Alphabetic'
    return value_tag

def get_raw_tag_value(med_volume, tag, alternative_tag=None, force_raw=False):
    """
    Gets the value of a tag, regardless of its location in the header. A tag is always defined
    by its DICOM tag number.

    Parameters:
        med_volume (MedicalVolume): the volume to get the tag from
        tag (str): the DICOM tag identifier
        alternative_tag (str, optional): an alternative tag to use if the first one is not found
        force_raw (bool, optional): if True, the tag is always treated as a raw tag, don't try to get it from the standard header

    Returns:
        (Any): the value of the tag
    """
    if not force_raw:
        if tag in defined_tags:
            # tag is named
            named_tag = defined_tags[tag]
            if isinstance(named_tag, list):
                # tag is a list of tags. Find out what tag it actually is stored
                for t in named_tag[:]:
                    if t in med_volume.omids_header:
                        named_tag = t
                        break
            try:
                if isinstance(med_volume.omids_header[named_tag], list):
                    return list(map(defined_tags.get_translator(named_tag), med_volume.omids_header[named_tag]))
                else:
                    return defined_tags.get_translator(named_tag)(med_volume.omids_header[named_tag])
            except KeyError as e:
                if alternative_tag:
                    return get_raw_tag_value(med_volume, alternative_tag)
                else:
                    raise e

        if tag in patient_tags:
            # tag is named
            named_tag = patient_tags[tag]
            if isinstance(named_tag, list):
                # tag is a list of tags. Find out what tag it actually is stored
                for t in named_tag[:]:
                    if t in med_volume.patient_header:
                        named_tag = t
                        break
            if 'isList' in med_volume.patient_header[named_tag]:
                return list(map(patient_tags.get_translator(named_tag), med_volume.patient_header[named_tag]))
            else:
                return patient_tags.get_translator(named_tag)(med_volume.patient_header[named_tag])

    # tag is numeric
    value_tag = _get_value_tag(med_volume.extra_header[tag])
    return med_volume.extra_header[tag][value_tag]


def replace_volume(medical_volume, new_data):
    """ Replaces the volume of a medical volume with a new volume leaving the tags intact

        Parameters:
            medical_volume (MedicalVolume): the volume to replace
            new_data (np.ndarray): the new volume

        Returns:
            (MedicalVolume): the new volume
    """
    new_volume = MedicalVolume(new_data, medical_volume.affine)
    copy_headers(medical_volume, new_volume)
    return new_volume

def copy_volume_with_omids_headers(medical_volume):
    """ Creates a copy of a medical volume with the BIDS headers

    Parameters:
        medical_volume (MedicalVolume): the volume to copy

    Returns:
        (MedicalVolume): the copy of the volume

    """
    new_volume = MedicalVolume(medical_volume.volume, medical_volume.affine)
    copy_headers(medical_volume, new_volume)
    return new_volume


def headers_to_dicts(header_list):
    """
    this function takes a list of DICOM headers and converts them into a meta and a header dictionary
    It compresses the dictionary so that the tags that are common to all images are kept only once.

    Parameters:
        header_list (list): list of DICOM headers

    Returns:
        (dict, dict): the meta and the header dictionaries

    """
    if type(header_list) != list:
        header_list = header_list.squeeze().tolist()

    json_header_list = []
    for h in header_list:
        meta_header = h.file_meta.to_json_dict()
        # the following should already be in the json dict
        #meta_header['is_little_endian'] = h.is_little_endian
        #meta_header['is_implicit_VR'] = h.is_implicit_VR

        json_header_list.append({'meta': meta_header, 'header': h.to_json_dict()})

    # compress json header list
    compressed_meta = {}
    compressed_header = {}

    # this function is used to compress the meta and header dictionaries
    def process_tag(tag, content, index, dest_dictionary):
        if tag == '7FE00010': # remove pixel data
            vr_type = content['vr']
            dest_dictionary[tag] = {'vr': vr_type, 'InlineBinary': ''}
            return
        if tag not in dest_dictionary:
            dest_dictionary[tag] = content
            return
        existing_content = dest_dictionary[tag]
        if content == existing_content:
            #print("Content already exists", tag, existing_content)
            return  # do nothing if the content is the same as the other slices

        # append to existing content
        value_tag = _get_value_tag(existing_content)

        if 'isList' not in existing_content:  # content is not already a list
            existing_content['isList'] = True
            existing_content[value_tag] = [existing_content[value_tag]] * (index)  # replicate content until now

        existing_content[value_tag].append(content[value_tag])

    for i, element in enumerate(json_header_list):
        for tag, content in element['header'].items():
            process_tag(tag, content, i, compressed_header)
        for tag, content in element['meta'].items():
            process_tag(tag, content, i, compressed_meta)

    return compressed_meta, compressed_header


def dicts_to_headers(n_slices, compressed_header, compressed_meta = None):
    """
    Reverts the headers_to_dicts function and creates a list of DICOM headers from the compressed dictionaries.

    Parameters:
        n_slices (int): the number of slices in the volume
        compressed_header (dict): the header dictionary
        compressed_meta (dict): the meta dictionary

    Returns:
        (list): the list of DICOM headers
    """
    if not compressed_meta:
        compressed_meta = None # catch the case of an empty dictionary meta

    # decompress the headers

    dicom_dataset_list = []

    header_dict_list = []
    meta_dict_list = []

    # decompress header
    for i in range(n_slices):
        new_dict = {}
        for key, element in compressed_header.items():
            new_dict[key] = copy.deepcopy(element)
            if 'isList' in element:
                value_tag = _get_value_tag(element)
                try:
                    new_dict[key][value_tag] = element[value_tag][i]
                    new_dict[key].pop('isList')
                except IndexError:
                    #print(f'Warning: tag {key} not defined for image {i}')
                    new_dict.pop(key) # tag not defined for all images

        vr_std = 'OW'
        try:
            vr_std = new_dict['7FE00010']['vr']
        except:
            pass
        new_dict['7FE00010'] = {'vr': vr_std, 'InlineBinary': ''} # ensure empty pixel data
        new_header = pydicom.dataset.Dataset.from_json(new_dict)
        # ensure file meta
        if compressed_meta is not None:
            new_meta_dict = {}
            for key, element in compressed_meta.items():

                new_meta_dict[key] = copy.deepcopy(element)
                if 'isList' in element:
                    value_tag = _get_value_tag(element)
                    new_meta_dict[key][value_tag] = element[value_tag][i]
                    new_meta_dict[key].pop('isList')

            new_meta = pydicom.dataset.FileMetaDataset.from_json(new_meta_dict)
            new_header.file_meta = new_meta
            new_header.ensure_file_meta()
        else:
            new_meta = pydicom.dataset.FileMetaDataset()
            new_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
            new_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.4'
            new_header.file_meta = new_meta

        dicom_dataset_list.append(new_header)
    return dicom_dataset_list


def separate_headers(raw_header_dict):
    """
    this function separates the header into three dictionaries:
    the header with data useful for processing, the patient data, and the rest, which is needed for DICOM

    Parameters:
        raw_header_dict (dict): the header as a dictionary (returned from headers_to_dicts)

    Returns:
        (dict, dict, dict): the three dictionaries (bids, patient, raw)
    """

    def process_dict(output_dict, tag_dict, remove=False):
        for numerical_key, named_key in tag_dict.items():
            try:
                original_content = raw_header_dict[numerical_key]
            except KeyError:
                continue
            value_tag = _get_value_tag(original_content)
            try:
                translator = tag_dict.get_translator(numerical_key)

                if 'isList' in original_content:
                    output_dict[named_key] = list(map(translator, original_content[value_tag]))
                else:
                    output_dict[named_key] = translator(original_content[value_tag])

                if remove:
                    original_content[value_tag] = '' # do not remove the original content
            except KeyError:
                pass # key has no value


    patient_dict = {}
    process_dict(patient_dict, patient_tags, remove=True)
    bids_dict = {}
    process_dict(bids_dict, defined_tags)

    # in-plane phase encoding direction - recommended by BIDS
    # TODO: fix correct polarity
    pe_value = bids_dict['PhaseEncodingDirection']
    if pe_value == 'ROW':
        bids_dict['PhaseEncodingDirection'] = 'j'
    else:
        bids_dict['PhaseEncodingDirection'] = 'i'


    return bids_dict, patient_dict, raw_header_dict


def remerge_headers(bids_dict, patient_dict, raw_header_dict):
    """
    Re-merge the three dictionaries into one header dictionary.
    Parameters:
        bids_dict: the bids dictionary
        patient_dict: the patient dictionary
        raw_header_dict: the raw header dictionary

    Returns:

    """
    def process_dict(input_dict, tag_dict):
        for named_key, value in input_dict.items():
            try:
                numerical_key = tag_dict.inverse[named_key]
            except KeyError:
                print("Warning: unknown tag", named_key)
                continue

            found = False
            original_content = None
            if isinstance(numerical_key, list):
                for key_to_test in numerical_key:
                    try:
                        original_content = raw_header_dict[key_to_test]
                        numerical_key = key_to_test
                        found = True
                        break
                    except KeyError:
                        continue
            else:
                try:
                    original_content = raw_header_dict[numerical_key]
                    found = True
                except KeyError:
                    continue
            if not found:
                print("Warning: tag not found", named_key, numerical_key)
                continue
            value_tag = _get_value_tag(original_content)
            translator = tag_dict.get_translator(named_key)

            if 'isList' in original_content: # apply translator to each element
                original_content[value_tag] = list(map(translator, value))
            else:
                original_content[value_tag] = translator(value)

    #process_dict(bids_dict, defined_tags)
    process_dict(patient_dict, patient_tags)

    return raw_header_dict


def slice_volume_3d(medical_volume, slices_list):
    """
    This function extracts slices specified from the slices_list from the medical volume.

    Parameters:
        medical_volume (MedicalVolume): the medical volume
        slices_list (list): the list of slices to extract

    Returns:
        MedicalVolume: the extracted volume
    """

    n_dim = medical_volume.volume.ndim
    assert n_dim == 3, "Only 3D volumes are supported"
    new_volume = np.copy(medical_volume.volume[:,:,slices_list])

    headers = remerge_headers(medical_volume.omids_header, medical_volume.patient_header, medical_volume.extra_header)
    new_headers = {}
    for key, value in headers.items():
        if 'isList' in value: # value is a list
            new_value = copy.deepcopy(value)
            value_tag = _get_value_tag(value)
            new_value_list = []
            for sl in slices_list:
                try:
                    new_value_list.append(value[value_tag][sl])
                except IndexError:
                    print(value)
                    print(value_tag)
                    sys.exit(-1)
            if _list_all_equal(new_value_list):
                new_value[value_tag] = new_value_list[0]
                del new_value['isList']
            else:
                new_value[value_tag] = new_value_list

        else:
            new_value = copy.deepcopy(value)
        new_headers[key] = new_value
    new_bids, new_patient, new_raw = separate_headers(new_headers)
    new_volume = MedicalVolume(new_volume, medical_volume.affine)
    setattr(new_volume, 'omids_header', new_bids)
    setattr(new_volume, 'bids_header', new_bids)
    setattr(new_volume, 'patient_header', new_patient)
    setattr(new_volume, 'extra_header', new_raw)
    setattr(new_volume, 'meta_header', getattr(medical_volume, 'meta_header'))
    return new_volume


def concatenate_volumes_3d(volumes_list):
    """ This function concatenates a list of 3d volumes into one single 3D volume

    Parameters:
        volumes_list (list): the list of volumes to concatenate

    Returns:
        MedicalVolume: the concatenated volume
    """
    assert len(volumes_list) > 0, "volumes_list is empty"
    assert all(map(lambda x: x.volume.ndim == 3, volumes_list)), "Only 3D volumes are supported"

    volume_2D_sizes = [ (x.volume.shape[0], x.volume.shape[1]) for x in volumes_list ]
    assert _list_all_equal(volume_2D_sizes), "All volumes must have the same 2D size"

    # create the new pixel data
    new_volume = np.concatenate([x.volume for x in volumes_list], axis=2)

    n_slices_list = [x.volume.shape[2] for x in volumes_list]

    remerged_header_list = [ remerge_headers(x.omids_header, x.patient_header, x.extra_header) for x in volumes_list ]

    all_tags = remerged_header_list[0].keys()
    new_headers_dict = {}

    #iterate over all keys and concatenate the values
    for tag in all_tags:
        for header_index, header in enumerate(remerged_header_list):
            if tag not in new_headers_dict:
                new_headers_dict[tag] = copy.deepcopy(header[tag])
            value_tag = _get_value_tag(new_headers_dict[tag])
            if 'isList' in new_headers_dict[tag]:
                if 'isList' in header[tag]:
                    # the tag is a list before and after
                    new_headers_dict[tag][value_tag] += header[tag][value_tag]
                else:
                    # the tag is a list before, but not after
                    # extend the list of values with another list of copied values with the length as the number of slices
                    new_headers_dict[tag][value_tag] += [header[tag][value_tag]]*n_slices_list[header_index]
            else:
                if 'isList' in header[tag]:
                    # the tag is not a list before, but after yes.
                    new_headers_dict[tag]['isList'] = True # make it a list
                    n_slices_so_far = sum(n_slices_list[:header_index])
                    new_headers_dict[tag][value_tag] = [header[tag][value_tag]]*n_slices_so_far + new_headers_dict[tag][value_tag]
                else:
                    # the tag is not a list before and after
                    if new_headers_dict[tag] == header[tag]:
                        # the tag is the same before and after
                        pass
                    else:
                        # the tag is different before and after
                        # make it a list
                        new_headers_dict[tag]['isList'] = True  # make it a list
                        n_slices_so_far = sum(n_slices_list[:header_index])
                        new_headers_dict[tag][value_tag] = [header[tag][value_tag]] * n_slices_so_far + \
                                                           [new_headers_dict[tag][value_tag]] * n_slices_list[header_index]

    new_bids, new_patient, new_raw = separate_headers(new_headers_dict)
    new_volume = MedicalVolume(new_volume, volumes_list[0].affine)
    setattr(new_volume, 'omids_header', new_bids)
    setattr(new_volume, 'bids_header', new_bids) # for compatibility
    setattr(new_volume, 'patient_header', new_patient)
    setattr(new_volume, 'extra_header', new_raw)
    setattr(new_volume, 'meta_header', getattr(volumes_list[0], 'meta_header'))
    return new_volume


def group(medical_volume, key):
    """
        Converts a 3D medical volume to a 4D one by grouping the slices according to the key.

        Parameters:
            medical_volume (MedicalVolume): the 3D medical volume
            key (str): the key to group the slices by. Must be an entry in BIDS header

        Returns:
            MedicalVolume: the 4D medical volume with headers

    """

    assert hasattr(medical_volume, 'omids_header'), 'Error grouping: medical volume must have a bids header'
    assert medical_volume.ndim == 3, 'Error grouping: medical volume must be three dimensional'
    assert key in medical_volume.omids_header, f'Error: medical volume does not have {key}'

    indices_dict = OrderedDict({})
    all_values = medical_volume.omids_header[key]
    if type(all_values) != list:
        return medical_volume  # nothing to do

    # get all indices corresponding to separate values
    for index, value in enumerate(all_values):
        if type(value) == list:
            real_value = tuple(value)
        else:
            real_value = value
        if real_value not in indices_dict:
            indices_dict[real_value] = []
        indices_dict[real_value].append(index)

    array_stack = []

    try:
        items = sorted(indices_dict.items())
    except TypeError:
        print('Warning: could not sort indices_dict')
        items = indices_dict.items()

    for _,index_list in items:
        array_stack.append(medical_volume.volume[:, :, index_list])

    new_volume = np.stack(array_stack, axis=3)

    medical_volume_out = MedicalVolume(new_volume, medical_volume.affine)

    copy_headers(medical_volume, medical_volume_out)

    def group_tags(header):
        for tag, element in header.items():
            if type(element) != dict: continue
            if 'isList' in element:
                value_tag = _get_value_tag(element)
                new_value_list = [[] for x in range(new_volume.shape[2])]
                new_value_list_ok = True
                try:
                    for outer_index, inner_index_list in enumerate(indices_dict.values()):
                        for inner_list_index, value_index in enumerate(inner_index_list):
                            value = element[value_tag][value_index]
                            new_value_list[inner_list_index].append(value)

                except IndexError:
                    #print('IndexError', key, element)
                    new_value_list_ok = False
                if new_value_list_ok:
                    element[value_tag] = new_value_list
                    element['is4dList'] = True


    medical_volume_out.omids_header['FourthDimension'] = key
    medical_volume_out.omids_header[key] = [i[0] for i in items]  # only keep the different values
    group_tags(medical_volume_out.extra_header)
    group_tags(medical_volume_out.meta_header)

    return medical_volume_out


def ungroup(medical_volume):
    """
    Converts a 4D medical volume to a 3D one by ungrouping the slices.

    Parameters:
        medical_volume (MedicalVolume): the 4D medical volume

    Returns:
        MedicalVolume: the 3D medical volume with headers
    """


    assert hasattr(medical_volume, 'omids_header'), 'Error grouping: medical volume must have a bids header'
    assert 'FourthDimension' in medical_volume.omids_header, f'Error: medical volume does not have a FourthDimension key'

    if medical_volume.ndim == 3:
        # only unravel headers
        fourth_dimension_size = 1
    else:
        fourth_dimension_size = medical_volume.shape[3]

    n_slices = medical_volume.shape[2]
    new_shape = (medical_volume.shape[0], medical_volume.shape[1], medical_volume.shape[2]*fourth_dimension_size)
    if fourth_dimension_size > 1:
        # make sure that slices are the fastest-changing index loop, otherwise saving dicom fails
        new_volume = np.reshape(medical_volume.volume.transpose([0,1,3,2]), new_shape)
    else:
        new_volume = medical_volume.volume

    medical_volume_out = MedicalVolume(new_volume, medical_volume.affine)
    copy_headers(medical_volume, medical_volume_out)

    fourth_dimension_key = medical_volume.omids_header['FourthDimension']
    fourth_dimension_value = medical_volume.omids_header[fourth_dimension_key]
    new_fourth_dimension_value = list(itertools.chain(*[ [x]*n_slices for x in fourth_dimension_value ]))
    # multiply the value list

    def ungroup_tags(header):
        for tag, element in header.items():
            if type(element) != dict: continue
            if 'is4dList' in element:
                value_tag = _get_value_tag(element)
                new_value_list = list(
                    itertools.chain(
                        *[list(x) for x in zip(*element[value_tag])]
                        )) # reconcatenate element list
                element[value_tag] = new_value_list
                element.pop('is4dList')

    medical_volume_out.omids_header.pop('FourthDimension')
    medical_volume_out.omids_header[fourth_dimension_key] = new_fourth_dimension_value

    ungroup_tags(medical_volume_out.extra_header)
    ungroup_tags(medical_volume_out.meta_header)

    return medical_volume_out


def dicom_volume_to_bids(medical_volume):
    """
    Converts a medical volume to a BIDS medical volume by creating and attaching the appropriate BIDS headers.
    Parameters:
        medical_volume (MedicalVolume): the medical volume to convert

    Returns:
        MedicalVolume: the BIDS medical volume
    """


    compressed_meta_header, compressed_header = headers_to_dicts(medical_volume.headers())
    bids_dict, patient_dict, raw_header_dict = separate_headers(compressed_header)
    setattr(medical_volume, 'meta_header', compressed_meta_header)
    setattr(medical_volume, 'omids_header', bids_dict)
    setattr(medical_volume, 'bids_header', bids_dict) # for compatibility
    setattr(medical_volume, 'patient_header', patient_dict)
    setattr(medical_volume, 'extra_header', raw_header_dict)
    return medical_volume


def bids_volume_to_dicom(medical_volume, new_series=False):
    """
    Converts a BIDS medical volume to a medical volume by creating and attaching the appropriate DICOM headers.

    Parameters:
        medical_volume (MedicalVolume): the BIDS medical volume to convert
        new_series (bool): if True, a new series UID is created for the DICOM headers

    Returns:
        MedicalVolume: the medical volume that can be saved as DICOM
    """
    if 'FourthDimension' in medical_volume.omids_header:
        medical_volume = ungroup(medical_volume)

    omids_header = getattr(medical_volume, 'omids_header', {})
    meta_header = getattr(medical_volume, 'meta_header', None)
    patient_header = getattr(medical_volume, 'patient_header', {})
    extra_header = getattr(medical_volume, 'extra_header', {})
    merged_header = remerge_headers(omids_header, patient_header, extra_header)
    new_header_list = dicts_to_headers(medical_volume.shape[2], merged_header, meta_header)

    new_series_uid = generate_uid()
    for header in new_header_list:
        header.SOPInstanceUID = generate_uid()
        if new_series:
            header.SeriesInstanceUID = new_series_uid

    new_volume = MedicalVolume(medical_volume.volume, medical_volume.affine, new_header_list)

    return new_volume


def reduce(med_volume, index):
    """
    Reduces the dimension of a medical volume by only keeping the volume at the given index
    and fixing the headers accordingly

    Parameters:
        med_volume (MedicalVolume): the 4D medical volume to reduce
        index (int): The volume index to keep

    Returns:
        MedicalVolume: the 3D medical volume with headers
    """

    fourth_dimension_tag = med_volume.omids_header['FourthDimension']
    new_volume = med_volume.volume[:,:,:,index]
    new_volume = MedicalVolume(new_volume, med_volume.affine)
    copy_headers(med_volume, new_volume)
    new_volume.omids_header[fourth_dimension_tag] = [new_volume.omids_header[fourth_dimension_tag][index]]
    new_volume = ungroup(new_volume)
    del new_volume.omids_header[fourth_dimension_tag]
    return new_volume


def get_manufacturer(med_volume: MedicalVolume):
    """
    Gets the scanner manufacturer

    Parameters:
        med_volume (MedicalVolume): the volume to test

    Returns:
        str: the manufacturer always uppercase
    """

    manufacturer = get_raw_tag_value(med_volume, '00080070')[0]
    return manufacturer.upper()


def get_modality(med_volume: MedicalVolume):
    """
    Gets the imaging modality

    Parameters:
        med_volume (MedicalVolume): the volume to test

    Returns:
        str: the modality always uppercase
    """

    modality = get_raw_tag_value(med_volume, '00080060')[0]
    return modality.upper()
