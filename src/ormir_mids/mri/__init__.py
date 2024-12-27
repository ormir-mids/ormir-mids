from .sequences import modality_approximation, match_mri_modality, search_mri_sequence, acquisiton_dimension

CONTRAST_REGEX = r'(GAD(O|AVIST)?|[+-]?G[AD]*|GAD|[+-]?C|C?[+-]|CONTRAST|P[0O]ST|\d{0,2}(ML|CC)|ENHANCE|DOT|CONTR|INFUSION|INJECT|MINUTE|AFTER|LATE)'
MRI_MODALITIES_BIDS = [
    # BIDS MRI modalities: https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html
    'PDw',
    'T1w',
    'T2w',
    'T2starw',
    'FLAIR',
    'PDT2w',
    'T1rho',
    'T1map',
    'T2map',
    'T2star',
    'UNIT1', # Homogeneous (flat) T1-weighted MP2RAGE image
    'inplaneT1',
    'inplaneT2',
    'angio',
]

