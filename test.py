#!/usr/bin/env python3
import os
import sys

from ormir_mids.utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume
from voxel import DicomReader
from ormir_mids.utils.headers import reduce, dicom_volume_to_bids, get_raw_tag_value
from ormir_mids.utils.io import load_dicom, save_bids, load_omids, save_dicom

import ormir_mids.converters

INPUT_FOLDER = 'C:\\Users\\francesco\\Desktop\\Data\\MESE_Anon'
OUTPUT = 'C:\\Users\\francesco\\Desktop\\Data\\MESE_Nii\\test.nii.gz'
OUTPUT_FOLDER_DICOM = 'C:\\Users\\francesco\\Desktop\\Data\\dicom_test_out'
OUTPUT_FOLDER_DICOM_2 = 'C:\\Users\\francesco\\Desktop\\Data\\dicom_test_out_noecho'

TEST_ENHANCED = 'C:\\Users\\francesco\\Desktop\\Data\\Philips_MESE_T2.dcm'
TEST_SIEMENS = 'C:\\Users\\francesco\\Desktop\\Data\\MESE_Anon'

r = DicomReader(num_workers=0, ignore_ext=True, group_by='SeriesInstanceUID')
im = r.load(TEST_ENHANCED)
im_bids = dicom_volume_to_bids(im[0])

print(im_bids.volume.shape)

from ormir_mids.converters.mese_siemens import MeSeConverterSiemensMagnitude

from ormir_mids.converters.mese_philips import MeSeConverterPhilipsMagnitude, MeSeConverterPhilipsPhase, MeSeConverterPhilipsReconstructedMap

print(MeSeConverterSiemensMagnitude.is_dataset_compatible(im_bids))


converters = [
    MeSeConverterPhilipsMagnitude,
    MeSeConverterPhilipsPhase,
    MeSeConverterPhilipsReconstructedMap
]

for converter in converters:
    print(converter.is_dataset_compatible(im_bids))
    data_out = converter.convert_dataset(im_bids)
    save_bids(os.path.join('.', converter.get_directory(), converter.get_file_name('test')) + '.nii.gz', data_out)

sys.exit(0)
#
print(ormir_mids.converters.MeSeConverterSiemensMagnitude.find(INPUT_FOLDER))


med_volume = load_dicom(INPUT_FOLDER, 'EchoTime')
print(med_volume.shape)
save_bids(OUTPUT, med_volume)

med_volume_2 = load_bids(OUTPUT)
#save_dicom(OUTPUT_FOLDER_DICOM, med_volume_2)

new_vol = med_volume_2.volume[:,:,:,0]

new_vol = reduce(med_volume_2, 0)
save_dicom(OUTPUT_FOLDER_DICOM_2, new_vol)
