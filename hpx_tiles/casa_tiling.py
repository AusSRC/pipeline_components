#!/usr/bin/env python3

"""
HPX tiling of an image cube with CASA
For a given image cube and tiling map (defines the locations of the HPX tiles in the area covered by the image cube)
we will perform the regridding onto a template fits file based on the centre coordinates provided in the tiling map.
The tiling map [csv] is created by `generate_tile_pixel_map.py`.

The files will be written to an output directory under a subdirectory given by the observation id.
"""

import os
import sys
import numpy as np
import csv
import time
import argparse
import logging
from casatasks import imhead, imregrid, exportfits  # type: ignore
from regions import PolygonSkyRegion
from astropy.io import fits
from astropy import wcs
from astropy import units as u
from astropy_healpix import HEALPix
from astropy.coordinates import SkyCoord


logging.basicConfig(level=logging.INFO)


def tile_id_to_region(tile_id, nside=32):
    """Create PolygonSkyRegion region object for a HPX tile from corner coordinates

    """
    hp = HEALPix(nside=nside, order='ring', frame='icrs')
    corners = hp.boundaries_lonlat(tile_id, step=1) * u.deg
    ra, dec = corners.value
    corners_skycoord = SkyCoord(ra[0] * u.deg, dec[0] * u.deg, frame='fk5')
    region = PolygonSkyRegion(corners_skycoord)
    return region


def mask_regions(fits_image, region, mask_outside=True):
    """Given a FITS image and a region object, mask the pixels based on the regions

    Args:
        fits_image [str]:           Path to the FITS image file.
        region [PolygonSkyRegion]:  Region object containing pixel corner sky coordinates
        mask_outside [Boolean]:     If True: mask everything outside the region.
                                    If False: mask everything inside the region.

    Returns:
        np.ndarray: Masked data array, same shape as input fits image.

    """
    with fits.open(fits_image) as hdul:
        hdu = hdul[0]
        region_pixel = region.to_pixel(wcs.WCS(hdu.header).celestial)

        # NOTE: Assume first axes are RA and DEC from header. Raise error if not true.
        assert 'RA' in hdu.header['CTYPE1'], f"Fits header CTYPE1 should be RA. Got {hdu.header['CTYPE1']}."
        assert 'DEC' in hdu.header['CTYPE2'], f"Fits header CTYPE2 should be DEC. Got {hdu.header['CTYPE1']}."

        # Create mask array
        mask = region_pixel.to_mask().to_image(hdu.data.shape[-2:])
        mask_value = int(not mask_outside)
        if mask is None:
            mask = np.ones(hdu.data.shape[-2:]) * mask_value

        # Apply mask
        data = hdu.data
        if int(hdu.header['NAXIS']) == 4:
            data[:, :, mask == mask_value] = np.nan
        elif int(hdu.header['NAXIS']) == 3:
            data[:, mask == mask_value] = np.nan
        elif int(hdu.header['NAXIS']) == 2:
            data[mask == mask_value] = np.nan
        else:
            raise ValueError(f"Unexpected value for NAXIS in fits header ({hdu.header['NAXIS']})")

    return data


def create_nan_tile(original_image, template_fits, crpix1_and_2, outfile, overwrite=True):
    """@Erik Osinga

    Create a "tile" from an SB that's outside the tile using a template tile .fits file.
        i.e. Creates a tile with all-NaNs with the same freq and stokes axis as the original_image.


    original_image -- str       -- location of fits file of observation
    template_fits  -- str       -- location of tile template fits file (i.e. correct projection and NAXIS1 and NAXIS2)
    crpix1_and_2   -- [flt,flt] -- new value of CRPIX defining the centre of the tile
    outfile        -- str       -- name of output file written

    Simply masks the whole template tile .fits file and re-assign parameters CRPIX1 and CRPIX2
    to those given by the user. Makes sure the other axes (freq,stokes) are the same length as the input image
    but have the ordering of the template image

    Saves the result in a fitsfile "outfile"
    """
    # assumed values for CRPIX_1 (RA) CRPIX_2 (DEC)
    crpix1, crpix2 = crpix1_and_2

    header_options = ['CRVAL','CDELT','CRPIX','CUNIT'] # 'CTYPE',

    with fits.open(original_image) as hdul_o:
        with fits.open(template_fits) as hdul_t: #hdul_t will be overwritten with nan tile

            # Get NAXIS for template and input file
            naxis_template = hdul_t[0].header['NAXIS']
            naxis_original = hdul_o[0].header["NAXIS"]

            if naxis_original != naxis_template:
                raise ValueError(f"Please provide template file with same naxis as input cube. Currently its {naxis_template} vs {naxis_original}")

            # Check assumption that first two axes in the header are RA DEC
            assert "RA" in hdul_t[0].header["CTYPE1"], f"Expected RA in template.fits first axis, got {hdul_t[0].header['CTYPE1']}"
            assert "DEC" in hdul_t[0].header["CTYPE2"], f"Expected DEC in template.fits second axis, got {hdul_t[0].header['CTYPE2']}"

            # Make sure template follows the RA,DEC,freq,stokes axis ordering. Decided by technical-core team
            # NOTE: for intermediate partial tiles it was decided that we keep the ra, dec, stokes, freq order for mosaicking with linmos
            assert "STOKES" in hdul_t[0].header['CTYPE3'], "template fits file should have axis order RA,DEC,STOKES,FREQ"
            assert "FREQ" in hdul_t[0].header['CTYPE4'], "template fits file should have axis order RA,DEC,STOKES,FREQ"

            # Update BMAJ and BMIN in header where appropriate
            try:
                hdul_t[0].header["BMAJ"] = hdul_o[0].header["BMAJ"]
                hdul_t[0].header["BMIN"] = hdul_o[0].header["BMIN"]
            except Exception as e:
                logging.warning(f'Update BMAJ and BMIN in header failed: {e}')

            # which leads to assumption that last two axes in numpy array are DEC, RA
            shape_o = hdul_o[0].data.shape[:-2]
            shape_t = hdul_t[0].data.shape[2:]
            # new tile should be same RA,DEC shape as template, but freq,stokes shape from original file
            shape_new = shape_o + shape_t

            # create NaN tile data shape
            data_new = np.zeros(shape_new, dtype=np.float32) * np.nan  # Make sure dtype is float32

            # Check if the input file has the same axis ordering of the template file.
            # By default, we expect cubes to have RA,DEC,STOKES,FREQ
            # but the template fits file will have RA,DEC,FREQ,STOKES

            axis_dict = {}
            # Input image and template image 3rd / 4th axis is the same:
            if hdul_t[0].header['CTYPE3'] == hdul_o[0].header['CTYPE3']:
                axis_dict[3] = 3
            if hdul_t[0].header['CTYPE4'] == hdul_o[0].header['CTYPE4']:
                axis_dict[4] = 4
            # Input image and template image 3rd / 4th axis is different
            if hdul_t[0].header['CTYPE3'] == hdul_o[0].header['CTYPE4']:
                axis_dict[3] = 4
            if hdul_t[0].header['CTYPE4'] == hdul_o[0].header['CTYPE3']:
                axis_dict[4] = 3

            # Take 3rd and 4th axis values from input image and put them into header in correct order
            for option in header_options:
                for i in range(3, naxis_original + 1):  # i.e. [3,4] if NAXIS=4
                    # if verbose
                    logging.info(f'Setting hdul_t {option}{i} from {hdul_t[0].header[f"{option}{i}"]} to {hdul_o[0].header[f"{option}{axis_dict[i]}"]}')

                    hdul_t[0].header[f"{option}{i}"] = str(hdul_o[0].header[f"{option}{axis_dict[i]}"])

            # If input image and template image had different axis ordering, we have to swap data axes
            if (axis_dict[3] == 4) and (axis_dict[4] == 3):
                # Go to STOKES,FREQ,RA,DEC
                data_new = np.moveaxis(data_new, 1, 0)
                logging.info(f'Swapped input data 3rd and 4th axis. Shape now is {data_new.shape}')

            # adjust header CRPIX as well
            hdul_t[0].header["CRPIX1"] = crpix1
            hdul_t[0].header["CRPIX2"] = crpix2
            for i in range(2,len(shape_new)):
                # remember start counting at NAXIS1, so NAXIS3 is first non-angular coordinate
                # and np.array() is inverted shape from fits header
                # print(f"NAXIS{i+1} = {shape_new[::-1][i]}" )

                hdul_t[0].header[f"NAXIS{i}"] = shape_new[::-1][i]
                hdul_t[0].header[f"NAXIS{i}"] = shape_new[::-1][i]

            hdul_t[0].data = data_new
            hdul_t[0].writeto(outfile, overwrite=overwrite)  # should be the first of its name


def parse_args(argv):
    parser = argparse.ArgumentParser("Generate tiles for a specfic SB.")
    parser.add_argument("-i", dest="obs_id", help="Observation ID.", required=True)
    parser.add_argument("-c", dest="cube", help="Image cube.", required=True)
    parser.add_argument("-t", dest="template", help="The template fits file.", required=True)
    parser.add_argument("-m", dest="map", help="Tiling map for the image cube [csv].", required=True)
    parser.add_argument("-o", dest="output", help="Output write directory for tiles cubes.", required=True)

    # Optional
    parser.add_argument("-n", dest="naxis", type=int, required=False, default=2048)
    parser.add_argument(
        "-p",
        dest="prefix",
        type=str,
        help="Prefix for output tile filenames",
        required=False,
        default="PoSSUM"
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Run with the following command:

        python casa_tiling.py
            -i <obs_id>
            -c <image_cube>
            -m <tile_map>
            -o <output_dir>
            -t <template>

    Optional arguments:
        -n naxis        Naxis for tiling (default 2048)
        -p prefix       Output tile filename prefix (default "PoSSUM")

    """
    args = parse_args(argv)
    obs_id = args.obs_id
    image_cube = args.cube
    tiling_map = args.map
    output_dir = args.output
    tile_template = args.template
    naxis = args.naxis
    prefix = args.prefix

    # Check files exist for image cube, tiling map, and tile template
    assert os.path.exists(image_cube), f'Input image {image_cube} not found.'
    assert os.path.exists(tiling_map), f'Input sky tiling map {tiling_map} not found.'
    assert os.path.exists(tile_template), f'Input tile template {tile_template} not found.'

    # Create output directories if they do not exist
    if not os.path.exists(output_dir):
        logging.info(f'Output directory not found. Creating new directory: {output_dir}')
        os.makedirs(output_dir, exist_ok=True)

    # Read tiling map
    pixel_ids = []
    crpix1 = []
    crpix2 = []
    with open(tiling_map, mode='r') as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            pixel_ids.append(float(row['PIXELS']))
            crpix1.append(float(row['CRPIX_RA']))
            crpix2.append(float(row['CRPIX_DEC']))

    # Read input image cube header
    logging.info('Getting header')
    fitsheader = imhead(image_cube)
    axis = fitsheader['axisnames']
    logging.info(axis)

    # Read tile template header
    logging.info('Getting regridding template')
    template_header = imregrid(imagename=tile_template, template='get', overwrite=True)

    # Starting the tiling
    logging.info('CASA tiling')
    start = time.time()
    for i, (ra, dec) in enumerate(zip(crpix1, crpix2)):
        pixel_id = int(pixel_ids[i])
        logging.info(f'Regridding tile {pixel_id} ({i+1} / {len(crpix1)})')
        inner_start = time.time()

        # Update the template header dictionary from / for imregrid
        template_header["csys"]["direction0"]["crpix"] = np.array([ra, dec])
        output_filename = "%s_%s-%d.image" % (prefix, obs_id, pixel_id)
        casa_image = os.path.join(output_dir, output_filename)
        fits_image = casa_image.split(".image")[0] + ".fits"

        # Continue if output already exists
        if os.path.exists(fits_image):
            logging.info(f'Output file already exists at {fits_image}. Skipping.')
            continue

        try:
            # Update template header
            if len(axis) == 4:
                fourth_axis = axis[3]
                if fourth_axis == "Frequency":
                    number_of_frequency = fitsheader["shape"][3]
                    template_header["shap"] = np.array(
                        [naxis, naxis, 1, number_of_frequency])
                third_axis = axis[2]
                if third_axis == "Frequency":
                    number_of_frequency = fitsheader["shape"][2]
                    template_header["shap"] = np.array(
                        [naxis, naxis, number_of_frequency, 1])
            if len(axis) == 3:
                third_axis = axis[2]
                if third_axis == "Frequency":
                    number_of_frequency = fitsheader["shape"][2]
                    template_header["shap"] = np.array(
                        [naxis, naxis, number_of_frequency])
                else:
                    template_header["shap"] = np.array([naxis, naxis, 1])

            # NOTE: CRPIX1 CRPIX2 correction for CASA tiling error
            # NOTE: The versions of CASA below are required for this correction to work correctly
            # casatools==6.5.2.26
            # casatasks==6.5.2.26
            template_header["csys"]["direction0"]["crpix"] = np.array([ra - 1.0, dec - 1.0])

            # Tiling to CASA image
            logging.debug('Performing CASA tiling')
            imregrid(
                imagename=image_cube,
                template=template_header,
                output=casa_image,
                axes=[0, 1],
                interpolation="cubic",
                overwrite=True
            )

            # Convert CASA image to fits image
            logging.debug('Converting CASA image to fits image')
            exportfits(
                imagename=casa_image,
                fitsimage=fits_image,
                overwrite=True,
                stokeslast=False
            )

            # Cleanup CASA image
            logging.debug('Deleting CASA image')
            os.system(f"rm -rf {casa_image}")
            logging.info('Tiling pixel %d completed in %.3f s' % (pixel_id, (time.time() - inner_start)))

        except Exception as e:
            logging.error(f'Error tiling {pixel_id} for observation {obs_id}. Generating NaN tile')
            logging.error(f'Error message: {e}')
            create_nan_tile(image_cube, tile_template, template_header["csys"]["direction0"]["crpix"], fits_image, overwrite=True)

    logging.info('Tiling for observation %s completed. Time elapsed is %.3f seconds.' % (obs_id, (time.time() - start)))
    return


if __name__ == "__main__":
    main(sys.argv[1:])
