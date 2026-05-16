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
import re

def remove_special_characters(text: str):
    """
    Keep only  the non-alphanumeric characters as well as _ + symbols

    in the text to clean and standardize text, which makes searching files easier

    Parameters
    ----------
    text: str
        The text to clean
    Returns
    -------
    text: str
        The cleaned text
    """
    # clean and standardize series_description descriptions, which makes searching files easier
    try:
        text = re.sub('[^a-zA-Z0-9 _\+\* ]', '', text)
    except:
        text = ''
    return text.upper()


def remove_nonalphanumeric(text: str):
    """
    Keep only  the non-alphanumeric characters as well as spaces

    in the text to clean and standardize text, which makes searching files easier

    Parameters
    ----------
    text: str
        The text to clean
    Returns
    -------
    text: str
        The cleaned text
    """
    # clean and standardize series_description descriptions, which makes searching files easier
    try:
        text = re.sub('[^a-zA-Z0-9]', '', text)
    except:
        text = ''
    return text


def extract_number(filename, pattern ='\\d+', default=0):
    """
    Extracts the first number from the file path using a regular expression.

    Parameters:
    - file_path: The path of the file as a string.

    Returns:
    - The extracted case number as a string, zero-padded to three digits.
    """
    # Regex pattern to find the first number followed by one or more digits
    match = re.search(pattern, filename)
    if match:
        return str(match.group(0)).zfill(3)  # Zero-pad the case number to three digits
    return str(default).zfill(3)  # Return a default value if no match is found
