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
from casatasks import imhead, imregrid, exportfits


logging.basicConfig(level=logging.INFO)


def parse_args(argv):
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

        try:
            # this is how I will update the dictionary
            template_header["csys"]["direction0"]["crpix"] = np.array([ra, dec])

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

            output_filename = "%s_%s-%d.image" % (prefix, args.obs_id, pixel_ID[i])
            output_name = os.path.join(write_dir, output_filename)

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
                fitsimage=output_name.split(".image")[0] + ".fits",
                overwrite=True,
                stokeslast=False)

            # delete all casa image files.
            logging.info("Deleting the casa image. ")
            os.system("rm -rf %s" % output_name)
        except Exception as e:
            logging.error(f"There was an exception: {e}")
            logging.info("Skipping pixel")
            # TODO: need to update csv file

    end_tiling = time.time()
    logging.info(
        "Tiling for observation %s completed. Time elapsed is %.3f seconds."
        % (args.obs_id, (end_tiling - start_tiling)))


if __name__ == "__main__":
    main(sys.argv[1:])
