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

import os
import re
import shutil
import argparse
from pathlib import Path
from subprocess import check_output

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Convert DICOM files to NIFTI format adopting the BIDS convention")
parser.add_argument("-d", "--dicomdir", default="./data/SpinalDiseaseDataset/sourcedata", help="Specify the DICOM directory. Default is './data/SpinalDiseaseDataset/sourcedata'")
parser.add_argument("-b", "--bidsdir", default="./data/SpinalDiseaseDataset", help="Specify the BIDS directory. Default is './data/SpinalDiseaseDataset'")
parser.add_argument("-p", "--pidp", default="SDD", help="Specify the PIDP value. Default is 'ID'")
args = parser.parse_args()

# Declare an array with BIDS MRI anatomical modalities suffixes
MR_ANAT_MODALITIES = "T1w|T2w|T2star|FLAIR|PD|PDT2|inplaneT1"  # localizer"

TMPDIR = os.path.join(args.bidsdir, "nifti")
os.makedirs(TMPDIR, exist_ok=True)

# Loop through each DICOM directory
for pdir in [d for d in os.listdir(args.dicomdir) if os.path.isdir(os.path.join(args.dicomdir, d))]:
    id = re.search(r'\d+', pdir).group()
    pid = f"{args.pidp}{int(id):04d}"
    print(" ------------------------------- ")
    print(f"Processing subject ID {id} into {pid}")
    print(" ------------------------------- ")

    ses = 1

    for sesid in [os.path.join(os.path.join(args.dicomdir, pdir), d) for d in os.listdir(os.path.join(args.dicomdir, pdir))]:
        os.makedirs(os.path.join(TMPDIR, f"sub-{pid}", f"ses-{ses}"), exist_ok=True)

        for sid in [os.path.join(sesid, d) for d in os.listdir(sesid) if os.path.isdir(os.path.join(sesid, d))]:
            # Run dcm2niix and capture its output
            # -b controls if json file is created
            # -m creates if a same series is merged
            # -z compresses the files
            # -f Creates the filename
            output = check_output(["dcm2niix", "-b", "n", "-z", "y", "-m", "y", "-f", f"sub-{pid}_ses-{ses}_run-%s_%c", "-o", os.path.join(TMPDIR, f"sub-{pid}", f"ses-{ses}"), sid])
            # output = check_output(["dcm2niix", "-b", "n", "-z", "y", "-m", "y", "-f", f"sub-{pid}_ses-{ses}_run-%s_echo-%e_%c", "-o", os.path.join(args.bidsdir, f"sub-{pid}", f"ses-{ses}"), sid])

            # Extract the filename from the output assuming the output contains only one converted file
            filepath = re.search(r'Convert \d+ DICOM as (.+)', output.decode('utf-8')).group(1)

            # Copy the extracted metadata from the dicom directory
            shutil.copy(os.path.join(sid, os.path.basename(sid) + ".json"), os.path.join(TMPDIR, f"sub-{pid}", f"ses-{ses}", os.path.basename(filepath) + ".json"))

        # Check if the file name matches the Equidistant resampled pattern
        for file in [f for f in os.listdir(os.path.join(TMPDIR, f"sub-{pid}", f"ses-{ses}")) if f.endswith(".nii.gz") and "Eq_" in f]:
            new_name = os.path.join(os.path.dirname(os.path.join(TMPDIR, f"sub-{pid}", f"ses-{ses}", file)), file.replace("_vp", "_desc-equidistant_vp"))
            new_name = new_name.rpartition("_Eq")[0] + ".nii.gz"
            os.rename(os.path.join(TMPDIR, f"sub-{pid}", f"ses-{ses}", file), new_name)

        # Loop through files in the source directory that match the pattern
        for file in [f for f in os.listdir(os.path.join(TMPDIR, f"sub-{pid}", f"ses-{ses}")) if f.endswith(".nii.gz") and "mod-MR-" in f]:
            modality = os.path.basename(file).split("mod-MR-")[1].split(".nii.gz")[0]

            # Check if the modality is in the list of MR_ANAT_MODALITIES
            if any(re.match(modality, m) for m in MR_ANAT_MODALITIES.split("|")):
                new_filename = os.path.basename(file).replace(f"mod-MR-{modality}", modality)
                dirpath = Path(args.bidsdir)/ f"sub-{pid}"/ f"ses-{ses}"/ "mr-anat"
                dirpath.mkdir(parents=True, exist_ok=True)
                # os.makedirs(os.path.join(args.bidsdir, f"sub-{pid}", f"ses-{ses:02d}", "mr-anat"), exist_ok=True)

                # Move and rename the file to the target directory
                shutil.move(str(Path(TMPDIR)/ f"sub-{pid}"/f"ses-{ses}"/file) , str(Path(args.bidsdir)/ f"sub-{pid}"/ f"ses-{ses}"/ "mr-anat"/ new_filename))

                # Move the corresponding JSON file
                shutil.move((Path(TMPDIR)/ f"sub-{pid}"/f"ses-{ses}", str(file).replace(".nii.gz", ".json")).as_posix(),  str(Path(args.bidsdir)/ f"sub-{pid}"/ f"ses-{ses}"/ "mr-anat"/ new_filename.replace(".nii.gz", ".json") ))

        ses += 1