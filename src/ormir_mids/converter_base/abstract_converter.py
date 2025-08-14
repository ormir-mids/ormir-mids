import os
from abc import ABC, abstractmethod
from ..utils.OMidsMedVolume import OMidsMedVolume as MedicalVolume


class Converter(ABC):

    children = None
    @classmethod
    def add_child(cls, child_cls):
        """ Adds a child class to the list of children for this converter class."""
        if cls.children is None:
            cls.children = []
        if child_cls not in cls.children:
            cls.children.append(child_cls)

    @classmethod
    def get_children(cls):
        """ Returns the list of child classes for this converter class."""
        if cls.children is None:
            return []
        return cls.children

    @classmethod
    def set_parent(cls, parent_cls):
        parent_cls.add_child(cls)

    def __init__(self):
        pass

    @classmethod
    @abstractmethod
    def get_name(cls):
        return 'Abstract converter'

    @classmethod
    @abstractmethod
    def get_directory(cls):
        pass

    @classmethod
    @abstractmethod
    def get_file_name(cls, subject_id: str):
        pass

    @classmethod
    @abstractmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        pass

    @classmethod
    @abstractmethod
    def convert_dataset(cls, med_volume: MedicalVolume):
        pass

    @classmethod
    def get_file_path(cls, subject_id):
        return os.path.join(subject_id, cls.get_directory(), cls.get_file_name(subject_id))

    @classmethod
    def find(cls, path):
        
        file_pattern = (cls.get_file_name('') + '.nii.gz').lower()

        found_files = []

        for root, dirs, files in os.walk(path):
            for f in files:
                if f.lower().endswith(file_pattern):
                    found_files.append(os.path.join(root, f))

        return found_files

    @classmethod
    def is_multiseries(cls):
        return False

    @classmethod
    def multiseries_concat_tag(cls):
        return 'EchoTime'


class RootConverter(Converter):
    """
    A root converter that can be used to find all converters.
    """

    @classmethod
    def get_name(cls):
        return 'RootConverter'

    @classmethod
    def is_dataset_compatible(cls, med_volume: MedicalVolume):
        # Every dataset is compatible with the root converter
        return True
