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
__version__ = "0.0.1"

import logging
from pathlib import Path

from ..structure.MIDS import create_tsvs
from ..utils.files import load_yaml


if __name__=='__main__':

    data_path = 'data/MRSpineSegChallenge'
    info_filepath = f'config/data/{Path(data_path).name}.yaml'

    dataset_info = dict(load_yaml(info_filepath)).get("dataset", load_yaml(info_filepath) ) if Path(info_filepath).exists() else dict()
    if Path(data_path).exists():
        create_tsvs(data_path, dataset_info= dataset_info)
    else:
        logging.info(f'Path {data_path} does not exist')