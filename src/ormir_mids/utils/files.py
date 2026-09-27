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

# -*- coding: utf-8 -*-
__author__ = "Maria Monzon"
__version__ = "0.1.0"

from typing import Optional, Union
from pathlib import Path
import json
import numpy as np
import logging
import yaml


def deserialize_dict(data: dict) -> dict:
    """ Deserialize a dictionary to convert it to a JSON compatible dictionary

    Parameters
    ----------
    data: str
        JSON Object serialized as a string.

    Returns
    ----------
    json_dict: dict
        Python object loaded be serialized into a JSON Object.
    """
    dict = {}

    class NumpyEncoder(json.JSONEncoder):
        """
        A method to handle default encoding for objects not serializable.

        Parameters:
            obj: The object to be encoded.

        Returns:
            The encoded object in a serializable format.
        """

        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return json.JSONEncoder.default(self, obj)

    json_str = json.dumps(data, cls=NumpyEncoder)

    return json.loads(json_str)



def load_json(filepath: [str, Path]) -> object:
    """ Load a JSON Object compressed as a binary fname or path

    Parameters
    ----------
    filepath: str, Path
        File name of JSON fname we want to load.

    Returns
    ----------
    image_slice: Object
        Python object loaded be serialized into a JSON Object.
    """
    try :
        with open(filepath, 'rt', encoding='UTF-8') as f:
            return json.load(f)
    except:
        return dict()

def save_json(data: object, filename: [str,Path],  path: Optional[Union[str,Path]]='', sort: Optional[bool]=False)-> None:
    """ Save a Python Object as JSON series_description fname

    Parameters
    ----------
    data: Object
        Python object loaded be serialized into a JSON Object.
    filename: str, Path
        File name of JSON fname we want to load.
    path: str, Path
        Target dicom_dir Path where to save the fname
    sort: bool
        Sort the keys of the JSON Object
    """

    fp = Path(path) / Path(filename).with_suffix('.json')
    fp.parent.mkdir(exist_ok=True, parents=True)
    try:
        with open(fp, 'w', encoding='UTF-8') as f:
            json.dump(data, f, sort_keys = sort, indent = 4, ensure_ascii = False)
    except:
        data = deserialize_dict(data)
        with open(fp, 'w', encoding='UTF-8') as f:
            json.dump(deserialize_dict(data), f, sort_keys = sort, indent = 4, ensure_ascii = False)


def load_yaml(filepath: [str, Path]) -> object:
    """ Load a Python Object with from  a YAML fname .yaml

    Parameters
    ----------
    filepath: str, Path
        File name of the fname we want to save.
    path: str, Path
        Target dicom_dir path where to save the fname
    Returns
    ----------
    image_slice: Object
        Python object loaded be serialized into a YAML stream.
    """
    data = object()
    try:
        with open(filepath, 'r') as fd:
            return yaml.safe_load(fd)
    except:
        logging.exception(f"The yaml file {filepath} could not be loaded")
    return data

def save_yaml(data: object, filename: [str,Path], path: Optional[Union[str,Path]]='')-> None:
    """ Save a Python Object with to disk in .yaml

    Parameters
    ----------
    data: Object
          Python objects to be serialized into a YAML stream.
    filename: str, Path
        File name of the fname we want to save.
    path: str, Path
        Target dicom_dir path where to save the fname
    """
    fp = Path(path) / Path(filename).with_suffix('.yaml')
    fp.parent.mkdir(exist_ok=True, parents=True)
    with open(fp, 'w') as f:
        yaml.safe_dump(data, f, sort_keys=False)
