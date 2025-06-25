from .OMidsMedVolume import OMidsMedVolume as MedicalVolume
import numpy as np
from scipy.ndimage import map_coordinates


def realign_medical_volume(source: MedicalVolume, destination: MedicalVolume, interpolation_order: int = 3):
    """Realign this volume to the image space of another volume. Similar to ``reformat_as``,
    except that it supports fine rotations, translations and shape changes, so that the affine
    matrix and extent of the modified volume is identical to the one of the target.


    Parameters:
        source (MedicalVolume): The volume to realign
        destination (MedicalVolume): The realigned volume will have the same extent and affine matrix of ``destination``.
        interpolation_order (int, optional): spline interpolation order.

    Returns:
        MedicalVolume: The realigned volume.
    """

    target = destination.volume
    print("Alignment target shape:", target.shape)

    # disregard our own slice thickness for the moment
    # calculate the difference from the center of each 3D "partition" and the real center of the 2D slice
    z_offset = 0

    # The following would be need to be used if the origin of the affine matrix was calculated on the middle of the
    # slice with thickness == slice spacing. But centering the converted dataset on the real center of the slice
    # seems to be the norm, hence the z_offset is 0
    # z_offset = (other_thickness/other.pixel_spacing[2]/2 - 1/2) #(other_thickness - other.pixel_spacing[2])/2

    shape_as_range = (np.arange(target.shape[0]),
                      np.arange(target.shape[1]),
                      np.arange(target.shape[2]) + z_offset)

    coords = np.array(np.meshgrid(*shape_as_range, indexing='ij')).astype(float)

    # Add additional dimension with 1 to each coordinate to make work with 4x4 affine matrix
    addon = np.ones([1, coords.shape[1], coords.shape[2], coords.shape[3]])
    coords = np.concatenate([coords, addon], axis=0)  # shape: [4, x, y, z]
    coords = coords.reshape([4, -1])  # shape: [4, x*y*z]

    # build affine which maps from target grid to source grid
    aff_transf = np.linalg.inv(source.affine) @ destination.affine

    # transform the coords from target grid to the space of source image
    coords_src = aff_transf @ coords  # shape: [4, x*y*z]

    # reshape to original spatial dimensions
    coords_src = coords_src.reshape((4,) + target.shape)[:3, ...]  # shape: [3, x, y, z]

    # Will create a image with the spatial size of coords_src (with is target.shape). Each
    # coordinate contains a place in the source image from which the intensity is taken
    # and filled into the new image. If the coordinate is not within the range of the source image then
    # will be filled with 0.
    src_transf_data = map_coordinates(source.volume, coords_src, order=interpolation_order)

    mv = MedicalVolume(src_transf_data, destination.affine, destination.headers())

    return mv