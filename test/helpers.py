import nibabel
import json
import requests
from pathlib import Path
import zipfile

def n_files_in_dir(directory):
    return sum(1 for _ in directory.iterdir())

def check_nib_shape(nii_path, shape):
    shape = tuple(shape)
    return nibabel.load(nii_path).shape == shape

def check_echo_times(json_path, echo_times_list):
    with open(json_path, 'r') as f:
        dataset_description = json.load(f)
    return dataset_description['EchoTime'] == echo_times_list

def download_and_extract(url, extract_dir):
    # Download
    response = requests.get(url, stream=True)
    zip_path = Path(extract_dir) / "temp.zip"
    zip_path.write_bytes(response.content)

    # Extract
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    print(f"Extracted {n_files_in_dir(extract_dir)} files")

    # Cleanup
    zip_path.unlink()