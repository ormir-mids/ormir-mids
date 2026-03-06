# ORMIR-MIDS

ORMIR-MIDS is both a specification and a package to standardiza Medical Image Data Structure (MIDS)
for Open and Reproducible Musculoskeletal Imaging Research ([ORMIR](https://ormircommunity.github.io/)). 
ORMIR-MIDS is based on the [BIDS](https://bids.neuroimaging.io/) data structure for brain imaging data and on [muscle-bids](https://github.com/muscle-bids/muscle-bids) for muscle MR imaging data.

[![GitHub license](https://img.shields.io/github/license/ormir-mids/ormir-mids)](https://github.com/ormir-mids/ormir-mids/blob/main/LICENSE)

### Main contributors

* [Donnie Cameron](https://www.linkedin.com/in/donnie-cameron-b76bbb63/?originalSubdomain=uk)
* [Francesco Santini](https://www.francescosantini.com/)
* [Jukka Hirvasniemi](https://bigr.nl/member/jukka/)
* [Maria Monzon Ronda](https://mariamonzon.github.io/)
* [Serena Bonaretti](https://sbonaretti.github.io/)
* [Gianluca Iori](https://github.com/gianthk)
* [Francesco Chiumento](https://www.linkedin.com/in/francescochiumento)
* [Simone Poncioni](https://www.artorg.unibe.ch/research/mb/group_members/staff/poncioni_simone/index_eng.html)
* [Michelle Alejandra Espinoza Hernandez](https://www.linkedin.com/in/michelleaespinosah/)
* [Youngjun Lee](https://www.linkedin.com/in/youngjun-lee-029268203) 

  
---

## Installation

To install ORMIR-MIDS via `pip` use the following command in your terminal:  
```shell
pip install ormir-mids
```
*Note*: The installation of ORMIR-MIDS requires the following [dependencies](dependencies.md)

### Development installation 
If you want to contribute to ORMIR-MIDS, start by cloning the repository:    
```shell
git clone https://github.com/ormir-mids/ormir-mids.git
```
Then, install via conda (in a separate virtual environment):
```commandline
conda env create -n ormir-mids
conda activate ormir-mids
```
or via `pip`:
    
```shell
cd ormir-mids
pip install .
pip install --upgrade nibabel # the default nibabel has bugs
```

--- 
## Usage 

To use ORMIR-MIDS in your code, import it as:  
```python
import ormir_mids
```
To run ORMIR-MIDS from terminal, the command is:
```shell
dcm2omids -anonymize <pseudo_name> -recursive <input_dir> <output_dir>
```
*Note*: `ormir-mids` can be used for two purposes: 
1. To convert DICOM data to the ORMIR-MIDS format
2. As a Python module to find, load, and interrogate ORMIR-MIDS-format data.
For further clarification, see the [demo notebook](https://github.com/ormir-mids/ormir-mids/blob/main/jupyter/ormir-mids-qmski24.ipynb)


--- 
## Documentation and tutorials 

To learn how to use ORMIR-MIDS:
- Read the [ORMIR-MIDS website](https://ormir-mids.github.io/) for background information about the standard and the package
- Run the [demo notebook](https://github.com/ormir-mids/ormir-mids/blob/main/jupyter/ormir-mids-dcm2omids.ipynb) either locally or on [![Binder](https://gesis.mybinder.org/badge_logo.svg)](https://gesis.mybinder.org/v2/gh/ormir-mids/ormir-mids.git/main?urlpath=%2Fdoc%2Ftree%2Fjupyter%2Formir-mids-dcm2omids.ipynb))    


---
## How to contribute

To contribute to ORMIR-MIDS:
- Install ORMIR-MIDS for development (see [above](#Development-installation))
- Create a branch and make your changes and/or additions. If you want to coordinate the development with the main maintainers, write to [Donnie Cameron](https://www.linkedin.com/in/donnie-cameron-b76bbb63/?originalSubdomain=uk)
or [Francesco Santini](https://www.francescosantini.com/)
- Commit your changes and send a pull request
- To write a new converter class, refer to the [Example Converter Class](https://github.com/ormir-mids/ormir-mids/blob/main/src/ormir_mids/converter_base/converter_template.py)


---
## API documentation

You can find the API documentation of ORMIR-MIDS on [Read the Docs](https://ormir-mids.readthedocs.io/en/latest/ormir_mids.html)


---
## Citation

When using ORMIR-MIDS, please cite the following abstract (paper coming in the next months!): 

*S. Bonaretti, M. A. Espinosa Hernandez, F. Chiumento, Y. Founas, M. Froeling, J. Hirvasniemi, G. Iori, Y. Lee, S. Matuschik, M. Monzon, F. Santini, D. Cameron.* 
***ORMIR-MIDS:An open standard for curating and sharing musculoskeletal imaging data.***
*24th International Workshop on Quantitative Musculoskeletal Imaging (QMSKI) The Barossa Valley, South Australia. November 3-8, 2024.*


--- 
## Licence 
ORMIR-MIDS is released under Apache 2.0


---
## Legal aspects
This code is freely available only for research purposes.
The software has not been certified as a medical device and, therefore, must not be used for diagnostic purposes.


---
## Acknowledgement

The development of ORMIR-MIDS specification and package started during the 2nd [ORMIR](https://ormircommunity.github.io/) workshop [Sharing and Curating Open Data in Musculoskeletal Imaging Research](https://github.com/ORMIRcommunity/2024_2nd_ORMIR_WS/blob/main/README.md) and is currently ongoing. 

ORMIR-MIDS is an extension of [muscle-BIDS](https://github.com/muscle-bids/muscle-bids), which was partly developed during the 1st [ORMIR](https://ormircommunity.github.io/) workshop [Building the Jupyter Community in Musculoskeletal Imaging Research](https://github.com/JCMSK/2022_JCW/blob/main/README.md). 

---

ReadMe file created using the [template](https://github.com/ORMIRcommunity/templates/blob/main/ORMIR_readme_template.md) of the [ORMIR community](https://www.ormir.org/) (version 1.0, 2023)
