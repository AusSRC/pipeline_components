#!/usr/bin/env python3

"""
This code performs the tiling of an image cube with CASA.
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
from casatasks import imhead, imregrid, exportfits # type: ignore
from astropy import units as u
from astropy_healpix import HEALPix
from regions import Regions
from astropy.io import fits
from astropy import wcs

logging.basicConfig(level=logging.INFO)

def tileID_to_region(tileID):
    """@Erik Osinga
    Input; tile ID
    Returns: Regions object (i.e. region) denoting the tile with hpx number "tileID"
    """
    Nside=32
    HPX_PIXEL = tileID
    hp = HEALPix(nside=Nside, order='ring', frame='icrs')
    corner = hp.boundaries_lonlat(HPX_PIXEL, step=1) * u.deg
    RA, DEC = corner.value
    RA = RA[0]
    DEC = DEC[0]
    polygon_string = 'polygon(%f, %f, %f, %f, %f, %f, %f, %f)'%(RA[0], DEC[0],  RA[1], DEC[1], RA[2], DEC[2], RA[3], DEC[3])
    with open("regionfile.reg", 'w') as f:
        f.write('# Region file format: DS9 astropy/regions')
        f.write('\n')
        f.write('fk5')
        f.write('\n')
        f.write(polygon_string)

    r = Regions.read("regionfile.reg")
    # clean up region file again
    os.system("rm regionfile.reg")

    return r

def mask_regions(fitsimage, region, maskoutside=True):
    """@Erik Osinga
    Given a FITS image and a DS9 region file, mask the pixels based on the regions.

    Args:
        fitsimage (str): Path to the FITS image file.
        ds9region (str): Path to the DS9 region file.
        maskoutside (bool): If True, mask everything outside the region.
                            If False, mask everything inside the region.

    Returns:
        np.ndarray: Masked data array, same shape as input fits image.
    """
    # Open the FITS file
    with fits.open(fitsimage) as hdu:
        # Read the region (assume its not a file but already a region object)
        r = region
        if len(r)>1:
            raise ValueError(f"Expected one region file but found {len(r)}")
        # Convert the region to a 2D pixel mask
        rpix = r[0].to_pixel(wcs.WCS(hdu[0].header).celestial)

        # assumes final 2 axes are DEC,RA axis.
        # fits.open() reads in reverse order, so if first two fits axes are RA,DEC we're good
        if ("RA" not in hdu[0].header['CTYPE1']) or ("DEC" not in hdu[0].header['CTYPE2']):
            raise ValueError("Assumed first two axes are RA,DEC. But they are not.")

        mask = rpix.to_mask().to_image(hdu[0].data.shape[-2:])

        if mask is None:
            # then the region is outside the image
            # mask everything
            if maskoutside:
                mask = np.zeros(hdu[0].data.shape[-2:])
            else:
                mask = np.ones(hdu[0].data.shape[-2:])

        naxes = hdu[0].header['naxis']

        if maskoutside:
            # Mask everything outside the region
            setmaskto = 0
        else:
            # Mask everything inside the region
            setmaskto = 1

        if naxes == 4:
            hdu[0].data[:, :, mask == setmaskto] = np.nan
        elif naxes == 3:
            hdu[0].data[:, mask == setmaskto] = np.nan
        elif naxes == 2:
            hdu[0].data[mask == setmaskto] = np.nan

        data = hdu[0].data

    return data

def parse_args(argv):#
    parser = argparse.ArgumentParser("Generate tiles for a specfic SB.")
    parser.add_argument("-i", dest="obs_id", help="Observation ID.", required=True)
    parser.add_argument("-c", dest="cube", help="Image cube.", required=True)
    parser.add_argument(
        "-m", dest="map", help="Tiling map for the image cube [csv].", required=True)
    parser.add_argument(
        "-o",
        dest="output",
        help="Output write directory for tiles cubes.",
        required=True,)
    parser.add_argument(
        "-t", dest="template", help="The template fits file.", required=True)

    # Optional
    parser.add_argument("-n", dest="naxis", type=int, required=False, default=2048)
    parser.add_argument(
        "-p",
        dest="prefix",
        type=str,
        help="Prefix for output tile filenames",
        required=False,
        default="PoSSUM",)
    args = parser.parse_args(argv)
    return args

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

            # Also check whether the template file has the same axes CTYPEs as the original input cube.
            # for i in range(naxis_original):
            #     # If not, then it's not a good template file
            #     ctype_o = hdul_o[0].header[f"CTYPE{i+1}"]
            #     ctype_t = hdul_t[0].header[f"CTYPE{i+1}"]
            #     if ctype_o[:2] != ctype_t[:2]: # checking first two characters should be good enough.
            #                                   # Because different "RA" and "DEC" projections should be fine.
            #         raise ValueError(f"CTYPE{i+1} is {ctype_o} in original image but {ctype_t} in template fits")

            # Check assumption that first two axes in the header are RA DEC
            assert "RA" in hdul_t[0].header["CTYPE1"], f"Expected RA in template.fits first axis, got {hdul_t[0].header['CTYPE1']}"
            assert "DEC" in hdul_t[0].header["CTYPE2"], f"Expected DEC in template.fits second axis, got {hdul_t[0].header['CTYPE2']}"
            # Make sure template follows the RA,DEC,freq,stokes axis ordering. Decided by technical-core team
            assert "FREQ" in hdul_t[0].header['CTYPE3'], "template fits file should have axis order RA,DEC,FREQ,STOKES"
            assert "STOKES" in hdul_t[0].header['CTYPE4'], "template fits file should have axis order RA,DEC,FREQ,STOKES"

            # which leads to assumption that last two axes in numpy array are DEC, RA
            shape_o = hdul_o[0].data.shape[:-2]
            shape_t = hdul_t[0].data.shape[2:]
            # new tile should be same RA,DEC shape as template, but freq,stokes shape from original file
            shape_new = shape_o + shape_t

            # create NaN tile data shape
            data_new = np.zeros(shape_new,dtype=np.float32)*np.nan # Make sure dtype is float32

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
                for i in range(3,naxis_original+1): #i.e. [3,4] if NAXIS=4
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

def check_and_swap_fits_axes(fits_filename):
    """
    Check the axes of a FITS file and swap them if necessary.

    The function ensures that the 3rd axis is 'FREQ' and the 4th axis is 'STOKES'.
        If, instead, the 3rd axis is 'STOKES' and the 4th axis is 'FREQ', it swaps them.

    If the FITS file has only two axes, a ValueError is raised.

    INPUTS:
    fits_filename : str
        Path to the FITS file to be checked and potentially modified.

    RETURNS:
    None
        The function modifies the FITS file in place if the axes need to be swapped.
    """
    with fits.open(fits_filename, mode='update') as hdul:
        hdr = hdul[0].header
        data = hdul[0].data

        if data.ndim < 4:
            raise ValueError("FITS file has only {data.ndim} axes, expected at least four axes.")

        # Check the CTYPE of axes
        ctype3 = hdr.get('CTYPE3', '').strip()
        ctype4 = hdr.get('CTYPE4', '').strip()

        if ctype3 == 'FREQ' and ctype4 == 'STOKES':
            # Axes are correct, no changes needed
            return
        elif ctype3 == 'STOKES' and ctype4 == 'FREQ':
            logging.info(f"Swapping 3rd and 4th axis of {fits_filename} to achieve RA,DEC,FREQ,STOKES")
            # Swap the axes and update the header and data
            data = np.swapaxes(data, 1, 0)  # Swap the 4th and 3rd axes (considering reversed shape)

            # Update header options
            header_options = ['CTYPE', 'CRVAL', 'CDELT', 'CRPIX', 'CUNIT']
            for option in header_options:
                hdr[f'{option}3'], hdr[f'{option}4'] = hdr[f'{option}4'], hdr[f'{option}3']

            # Overwrite the data and header in the FITS file
            hdul[0].data = data
            hdul.flush()  # Save changes to the file

def main(argv):
    """Run with the following command:

        python casa_tiling.py
            -i <obs_id>
            -c <image_cube>
            -m <tile_map>
            -o <output_dir>
            -t <template>

    Optional arguments

        -n naxis        Naxis for tiling (default 2048)
        -p prefix       Output tile filename prefix (default "PoSSUM")

    """
    args = parse_args(argv)

    # Check files exist for image cube, tiling map and tile template
    image = args.cube
    if not os.path.exists(image):
        raise Exception(f"Input image {image} not found.")
    tiling_map = args.map
    if not os.path.exists(tiling_map):
        raise Exception(f"Input sky tiling map {tiling_map} not found.")
    tile_template = args.template
    if not os.path.exists(tile_template):
        raise Exception(f"Input tile template {tile_template} not found.")

    # Output directories
    prefix = args.prefix
    #if not os.path.exists(args.output):
    try:
        logging.info(f"Output directory not found. Creating new directory: {args.output}")
        os.makedirs(args.output)
    except FileExistsError:
        pass

    write_dir = args.output
    #if not os.path.exists(write_dir):
    try:
        logging.info(f"Output subdirectory not found. Creating new directory: {write_dir}")
        os.makedirs(write_dir)
    except FileExistsError:
        pass

    naxis = args.naxis

    # Read tiling map
    pixel_ID = []
    crpix1 = []
    crpix2 = []
    with open(tiling_map, mode="r") as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            pixel_ID.append(float(row["PIXELS"]))
            crpix1.append(float(row["CRPIX_RA"]))
            crpix2.append(float(row["CRPIX_DEC"]))

    logging.info("Getting header")
    fitsheader = imhead(image)
    axis = fitsheader["axisnames"]
    logging.info(axis)

    # Read tile template header
    logging.info("Getting regridding template")
    template_header = imregrid(imagename=tile_template, template="get", overwrite=True)

    # Starting the tiling.
    logging.info("CASA tiling")
    start_tiling = time.time()
    for i, (ra, dec) in enumerate(zip(crpix1, crpix2)):
        logging.info(f"Regridding tile {i+1}/{len(crpix1)}")
        one_tile_start = time.time()

        # Update the template header dictionary from / for imregrid
        template_header["csys"]["direction0"]["crpix"] = np.array([ra, dec])
        output_filename = "%s_%s-%d.image" % (prefix, args.obs_id, pixel_ID[i])
        output_name = os.path.join(write_dir, output_filename)
        fitsimage = output_name.split(".image")[0] + ".fits"

        ##############
        # below lines added by Erik to
        # check if there are any non-NaN pixels in the tile region
        r = tileID_to_region(pixel_ID[i])
        masked_data = mask_regions(image, r, maskoutside=True)
        # if there are only NaN pixels, we don't need to make this tile from the current observation
        # we can simply create a tile with all-NaN in case it needs to be combined with different freqs
        if np.isnan(masked_data).all():
            logging.warning("WARNING: Tile is outside the observation. If this is the case for all frequencies, then the tile does not actually require this observation.")
            # todo: check/log this somehow? It would verify the radius needed for the tile
            logging.info(f"Creating NaN tile {fitsimage}")
            create_nan_tile(image, tile_template, template_header["csys"]["direction0"]["crpix"], fitsimage, overwrite=True)
        ##############

        else: # if there are finite value pixels, proceed as before
            try:
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

                # tiling, outputs tile fits in CASA image.
                imregrid(
                    imagename=image,
                    template=template_header,
                    output=output_name,
                    axes=[0, 1],
                    interpolation="cubic",
                    overwrite=True,)

                # convert casa image to fits image
                one_tile_end = time.time()
                logging.info(
                    "Tiling of pixel ID %d completed. Time elapsed %.3f seconds. "
                    % (pixel_ID[i], (one_tile_end - one_tile_start)))

                logging.info("Converting the casa image to fits image.")
                exportfits(
                    imagename=output_name,
                    fitsimage=fitsimage,
                    overwrite=True,
                    stokeslast=False
                )

                # delete all casa image files.
                logging.info("Deleting the casa image. ")
                os.system("rm -rf %s" % output_name)
            except Exception as e:
                logging.error(f"There was an exception: {e}")
                logging.info(f"Skipping tile {fitsimage}")
                continue
                # TODO: need to update csv file

        # Finally, check the axes ordering of the tiled image. Enforce RA,DEC,FREQ,STOKES
        check_and_swap_fits_axes(fitsimage)

    end_tiling = time.time()
    logging.info(
        "Tiling for observation %s completed. Time elapsed is %.3f seconds."
        % (args.obs_id, (end_tiling - start_tiling)))


if __name__ == "__main__":
    main(sys.argv[1:])
