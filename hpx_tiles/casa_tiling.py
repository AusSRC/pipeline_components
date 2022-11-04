#!/usr/bin/env python3

import os
import sys
import numpy as np
import csv
import time
import argparse
import json
import logging
from casatasks import imhead, imregrid, exportfits


logging.basicConfig(level=logging.INFO)


def main(argv):
    """Run with the following command:

        python casa_tiling.py
            -i <image_cube>
            -m <tile_map>
            -o <output_dir>
            -j <json_config>

    """
    # Load configuration
    parser = argparse.ArgumentParser("Generate tiles for a specfic SB.")
    parser.add_argument("-i", dest="image", help="Image cube.", required=True)
    parser.add_argument("-m", dest="map", help="Tiling map for the image cube.", required=True)
    parser.add_argument("-o", dest="output", help="Output write directory for tiles cubes.", required=True)
    parser.add_argument("-j", dest="json", help="The default JSON configuration file.", required=True)
    args = parser.parse_args(argv)
    with open(args.json, "r") as read_file:
        tile_config = json.load(read_file)

    # Read image, sky tiling map and tile template
    image = args.image
    if not os.path.exists(image):
        raise Exception(f"Input image {image} not found.")

    tiling_map = args.map
    if not os.path.exists(tiling_map):
        raise Exception(f"Input sky tiling map {tiling_map} not found.")

    tile_template = tile_config["tile_template"]
    if not os.path.exists(tile_template):
        raise Exception(f"Input tile template {tile_template} not found.")

    # Outputs
    naxis = tile_config["naxis"]
    output_prefix = tile_config["tile_prefix"]
    if not os.path.exists(args.output):
        os.mkdir(args.output)

    sbid = tiling_map.split("/")[-1].split("_")[-1].split(".")[0]
    write_dir = os.path.join(args.output, sbid)
    if not os.path.exists(write_dir):
        os.mkdir(write_dir)
        logging.info(f"Output directory not found. Creating new directory: {write_dir}")

    # Read tiling map
    crpix1 = []
    pixel_ID = []
    crpix2 = []

    with open(tiling_map, mode="r") as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            pixel_ID.append(float(row["PIXELS"]))
            crpix1.append(float(row["CRPIX_RA"]))
            crpix2.append(float(row["CRPIX_DEC"]))

    logging.info('Getting header')
    fitsheader = imhead(image)
    axis = fitsheader["axisnames"]
    logging.info(axis)

    # Read tile template header
    logging.info('Getting regridding template')
    template_header = imregrid(
        imagename=tile_template,
        template="get",
        overwrite=True
    )

    # Starting the tiling.
    logging.info('Tiling')
    start_tiling = time.time()
    for i, (ra, dec) in enumerate(zip(crpix1, crpix2)):
        logging.info(f"Producing tile {i+1}/{len(crpix1)}")
        one_tile_start = time.time()

        try:
            # this is how I will update the dictionary
            template_header["csys"]["direction0"]["crpix"] = np.array([ra, dec])

            if len(axis) == 4:
                fourth_axis = axis[3]
                if fourth_axis == "Frequency":
                    number_of_frequency = fitsheader["shape"][3]
                    template_header["shap"] = np.array(
                        [naxis, naxis, 1, number_of_frequency]
                    )

                third_axis = axis[2]
                if third_axis == "Frequency":
                    number_of_frequency = fitsheader["shape"][2]
                    template_header["shap"] = np.array(
                        [naxis, naxis, number_of_frequency, 1]
                    )

            if len(axis) == 3:
                third_axis = axis[2]
                if third_axis == "Frequency":
                    number_of_frequency = fitsheader["shape"][2]
                    template_header["shap"] = np.array(
                        [naxis, naxis, number_of_frequency]
                    )
                else:
                    template_header["shap"] = np.array([naxis, naxis, 1])

            outputname = args.output + "%s-%s-%d.image" % (output_prefix, sbid, pixel_ID[i])

            # tiling, outputs tile fits in CASA image.
            imregrid(
                imagename=image,
                template=template_header,
                output=outputname,
                axes=[0, 1],
                interpolation="cubic",
                overwrite=True,
            )
            # convert casa image to fits image
            one_tile_end = time.time()
            logging.info(
                "Tiling of pixel ID %d completed. Time elapsed %.3f seconds. "
                % (pixel_ID[i], (one_tile_end - one_tile_start))
            )

            logging.info("Converting the casa image to fits image.")
            exportfits(
                imagename=outputname,
                fitsimage=outputname.split(".image")[0] + ".fits",
                overwrite=True
            )
            # delete all casa image files.
            logging.info("Deleting the casa image. ")
            os.system("rm -rf %s" % outputname)
        except Exception as e:
            logging.error(f'There was an exception: {e}')
            logging.info('Skipping pixel')
            # TODO: need to update csv file

    end_tiling = time.time()
    logging.info(
        "Tiling for SB%s completed. Time elapsed is %.3f seconds."
        % (sbid, (end_tiling - start_tiling))
    )


if __name__ == "__main__":
    main(sys.argv[1:])
