# -*- coding: utf-8 -*-

# Copyright (c) Maria Monzon, BMDS ETH Zurich
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file_metadata except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# See the License for the specific language governing permissions and
# limitations under the License.

import re

MRI_MODALITIES = {
    'localizer': {'localizer|localiser|survey|loc\.|\bscout\b|(?=.*plane)(?=.*loc)|(?=.*plane)(?=.*survey)|3-plane|^loc*|Scout|AdjGre|topogram|three_plane_loc|3plane|3_plane|three_plane|POSDISP|POS'},
    'CAL': {'(?=.*HO)(?=.*shim)|\bHOS\b|_HOS_|.*shim|calibration|calib*'},
    'BOLD': {'bold|fmri|resting|rest'},
    'B0': { '(?=.*field)(?=.*map)|(?=.*bias)(?=.*ch)|field|fmap|topup|DISTORTION|se[-_][aprl]{2}$'},
    'ADC': { '_ADC$|^ADC|isoADC|AvDC|Average_DC|_TRACEW$|APPARENT DIFFUSION|APPARENT DIFFUSION COEFFICIENT'},
    'FLAIR': { '(?=.*flair)|(?=.*FLAIR)|(?=.*FluidAttenuatedInversionRecovery)|(?=.*CSFSuppressed)|FLUIDATTENUATEDINVERSIONRECOVERY| (?=.*\b{DARK\b)(?=.*\b{FLUID}\b)|FLAIR'},
    'PDw': {'(\bPD\b)|(_PD_)|(_PD)|(PD_)' },
    'T2starw': {'(\bT2\*\b)|(_T2\*_)|(_T2\*)|(T2\*_)|(T2\*)|(t2star)|t2starw'},
    'T1rho': { '(\bT1rho\b)|(_T1rho_)|(_T1rho)|(T1rho_)|^t1rho|_t1rho$|_t1rho_'},
    'UNIT1': {'MPRAGE|(?i)mprage'},
    'MRV': {'^mrv|^mrv$|mrv|mrv$'},
    'MRA': { '^mra|_mra$|_mra_'},
    'PWI': {'asl|(?=.*blood)(?=.*flow)|(?=.*art)(?=.*spin)|tof|perfusion|angio|cbf|cerebral_blood_flow|cbv|rBV_map|rBF_map|mtt_map|ttp_rgb'},
    'SWI': {'swi|susceptibility|suscept|swan|Mag images|Mag_images|Pha_images|Pha images|SW'},
    'DWI': { 'dti|dwi|diff|diffu|ddiffu|diffusion|difusion|(?=.*diff)(?=.*dir)|hardi'},
    'T2w': {'(?=.t2)|t2w?|ciss|fiesta|haste' },
    'T1w': {'(?=.t1)|t1w?|(?!.*inplane)(?=.*3d anat)|(?!.*inplane)(?=.*3d)(?=.*bravo)|bravo|spgr|stir'}
}
MRI_SEQUENCES_REGEX = {
    # "STIR": r"(?i)(Turbo[\s\-_]*STIR|Fast[\s\-_]*STIR|STIR)",
    "MPRAGE": r"(?i)MPRAGE",
    "PROPELLER": r"(?i)(PROPELLER|BLADE|MultiVane|VANE|RADAR|JET)",
    "DESPOT1": r"(?i)(DESPOT1|VFA[\s\-_]*T1)",
    "DESPOT2": r"(?i)(DESPOT2|VFA[\s\-_]*T2)",
    "FSE": r"(?i)(FAST[\s\-_]*SPIN[\s\-_]*ECHO|TURBO[\s\-_]*SE|FAST[\s\-_]*SE|SSH\-TSE|UFSE|SSTSE|HASTE|SS\-FSE|TSE|CUBE|VISTA|isoFSE|FSE)",
    "IR": r"(?i)(INVERSION[\s\-_]*RECOVERY|IR[\s\-_]*RSE|IRM|TIRM|Fast[\s\-_]*IR|FSE\-IR|FIR|IR)",
    "SSGE": r"(?i)(SteadyState[\s\-_]*GE|BFFE|FFE|FISP|MPGR|GRE|TRSG|SSGE)",
    "SGE": r"(?i)(SPOILED[\s\-_]*GE|FFE|FLASH|SPGR|MPSPGR|RSSG|RF\-spoiled)",
    "FGE": r"(?i)(FAST[\s\-_]*GE|FFE|TFE|THRIVE|TurboFLASH|VIBE|BRAVO|FGRE|Fast[\s\-_]*SPGR|FMPSPGR|VIBRANT|FAME|LAVA|R\-TFE|T1\-TurboFLASH|FSPGR)",
    "SE": r"(?i)(SE|SPIN[\s\-_]*ECHO)",
    "GRE": r"(?i)(FFE|GRE|GE|FE)",
    "SSFP": r"(?i)(SSFP|FIESTA|TRUEFISP|B\-FFE)",
    "PC": r"(?i)(PHASE[\s\-_]*CONTRAST|PC)",
    "TOF": r"(?i)(TIME[\s\-_]*OF[\s\-_]*FLIGHT|TOF)",
    "EPI": r"(?i)(EPI|EPI[\s\-_]*DWI)",
}


def match_mri_modality(series_description: str):
    """ Helper function to find the MRI modality from the DICOM description tag.
    Parameters:
    -----------
    series_description: str
        The DICOM description tag string
    Returns:
    --------
    modality: str
        The MRI modality (T1, T2, T2*, FLAIR, DWI, BOLD)
    """
    modality = None  # Default value

    # Perform regex search for each pattern
    for mri_mod, mri_params in MRI_MODALITIES.items():
        pattern = mri_params
        match = re.search(pattern, series_description, re.IGNORECASE)
        if match:
            modality = mri_mod
            break
    return modality

def modality_approximation(echo_time: [int, float], repetition_time: [int, float], inversion_time: [int, float],
                           default_sequence: str = ""):
    """ Function to approximate sequence to T1, T2 and FLAIR based on Long/short RT ET.
    References:
    - https://case.edu/med/neurology/NR/MRI%20Basics.htm
    - https://www.imaios.com/en/e-mri/nmr-signal-and-mri-contrast/signal-weighting-and-sequences-parameters
    - https://www.sciencedirect.com/science/article/pii/S2213158219301998

    Parameters:
    ----------
    echo_time: [int, float]
        time [ms] between the middle of the excitation pulse and the peak of the echo produced

    repetition_time:
        time [ms] between the beginning of a pulse sequence and the beginning of the next pulse sequence.

    inversion_time:
        time [ms]  between the middle of the inversion pulse and the middle of the excitation pulse

    default_sequence: str
        The default sequence type to return if no sequence type is found
    Returns:
    --------
    sequence_type: str
        The sequence type (T1, T2, FLAIR, PD)
    """
    sequence_times = {
        "PD": {"RT": 2000, "ET": 30, "IT": 0},  # PD typically TR = 1000-3000 ms, TE = 10-30 ms
        "T1": {"RT": 800, "ET": 30, "IT": 0},  # T1 typically TR = 400-2000 ms, TE = 10-30 ms
        "T2": {"RT": 500, "ET": 50, "IT": 0},  # T2 typically  TR = 500-2000 ms, TE = 10-30 ms
        "FLAIR": {"RT": 4500, "ET": 114, "IT": 2000},         # FLAIR typically TR = 4000-6000 ms, TE = 90-120 ms, TI = 2000-2500 ms
        "STIR": {"RT": 2415, "ET": 68, "IT": 160}   # STIR typically TR = 2500 ms, TE =70 ms, TI = 160 ms

    }
    # Initialize with default sequence specification in case no value is found (FSE)
    sequence_type = default_sequence

    inversion_time = float(inversion_time) if inversion_time is not None else 0
    echo_time = float(echo_time) if echo_time is not None else 0
    repetition_time = float(repetition_time) if repetition_time is not None else 0

    # Approximate sequence type
    if inversion_time > 250 and repetition_time > 1500:
        sequence_type = 'FLAIR'

    if inversion_time > 100 and repetition_time > 1500 and repetition_time < 2700 and echo_time < 100:
        sequence_type = 'STIR'

    elif echo_time < 30 and repetition_time < 800:
        sequence_type = 'T1w'

    elif echo_time > 50 and repetition_time < 2500:
        sequence_type = 'T2w'

    elif echo_time < 50 and repetition_time > 1000:
        sequence_type = 'PDw'

    return sequence_type


def search_mri_sequence(sequence_name: str, series_description: str = None) -> str:
    """
    Search for a given MRI sequence name in the MRI_SEQUENCES dictionary.

    Parameters:
    sequence_name (str): The name of the MRI sequence to search for.

    Returns:
    str: The key of the MRI sequence if found, otherwise 'Sequence not found'.
    """
    sequence = None
    # Perform regex search for each pattern

    for seq, pattern in MRI_SEQUENCES_REGEX.items():
        # pattern = mri_params['patterns']
        match = re.search(pattern, series_description.upper(), re.IGNORECASE)
        if match:
            sequence = seq.lower()
            break


    if not sequence:
        for seq, pattern in MRI_SEQUENCES_REGEX.items():
            #pattern = mri_params['patterns']
            match = re.search(pattern, sequence_name.upper(), re.IGNORECASE)
            if match:
                sequence = seq.lower()
                break

    return sequence


def acquisiton_dimension( acquisition_matrix: list[int]) -> str:
    """ Function to approximate the acquisition dimension from the acquisition matrix
    Parameters:
    ----------
    acquisition_matrix: list[int]
        The DICOM tag 'AcquisitionMatrix' (0018,1310) values generally representing
        [ frequency rows, frequency columns, phase rows, phase columns ]
    Returns:
    --------
    dimension: str
        The acquisition dimension (2D, 3D)
    """
    dimension = '3D'
    if sum(1 for value in acquisition_matrix if value > 0) >= 2:
        dimension = '2D'
    return dimension





