import nibabel
import json
import requests
from pathlib import Path
import zipfile
from zenodo_get import zenodo_get


def n_files_in_dir(directory):
    return sum(1 for _ in directory.iterdir())


def check_nib_shape(nii_path, shape):
    shape = tuple(shape)
    return nibabel.load(nii_path).shape == shape


def check_echo_times(json_path, echo_times_list):
    with open(json_path, "r") as f:
        dataset_description = json.load(f)
    return dataset_description["EchoTime"] == echo_times_list

def load_json(json_path):
    with open(json_path, "r") as f:
        return json.load(f)


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


def zenodo_download_and_extract(url, extract_dir):
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Download using zenodo-get with proper arguments
    print(f"Downloading from {url}...")
    args = ["-o", str(extract_dir), url]
    zenodo_get(args)

    # Look for zip files in the downloaded content
    zip_files = list(extract_dir.glob("*.zip"))

    if not zip_files:
        print("No zip files found in the downloaded content")
        return

    # Extract all zip files
    for zip_path in zip_files:
        print(f"Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        zip_path.unlink()

    print(f"Extracted {n_files_in_dir(extract_dir)} files")
