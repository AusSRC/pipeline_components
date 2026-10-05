#!/usr/bin/env python3

"""
This script generates tile footprints containing HealPix ID, CRPIX1/2 and CRVAL1/2.
Inputs:
    1. Footprint region files. Supports only .txt or reg. The region file name
        should be something like name..._ID.reg/txt, where name can be anything the
        user chose to name the footprints, and ID is the SB ID e.g. '2156-54' (corresponds
        sb10040).
    2. Tile setting. HealPix nside, image CDELT. See input json file 'AllSky-TileConfig.json.

Output:
    1. A csv file containing a list tile IDs and the corresponding SBs. This file is used
        to identify HealPix pixels that finds contribution from multiple SBs.
    2. A csv file for each SB containg pixes parameters (CRPIX) used for generating tiles.

Author: Lerato
"""

import argparse
import csv
import json
import logging
import os
import sys

import numpy
import pandas as pd
import pyregion
from astropy import units as u
from astropy.coordinates import Angle
from astropy.io import fits
from astropy.wcs import WCS
from astropy_healpix import HEALPix

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hms2deg(hms):
    """Converts unit from hms to degrees"""

    h, m, s = hms.split(":")
    a = Angle(f"{h}h{m}m{s}")
    return a.deg


def dms2deg(dms):
    """Converts unit from dms to degrees"""

    d, m, s = dms.split(":")
    a = Angle(f"{d}d{m}m{s}")
    return a.deg


def get_deg(hms_array, dms_array):
    """Converts unit of an array from hms to degrees"""

    conversion_hms = []
    conversion_dms = []
    for hms, dms in zip(hms_array, dms_array):
        conversion_hms.append(hms2deg(hms))
        conversion_dms.append(dms2deg(dms))
    return conversion_hms, conversion_dms


def points_within_circle(x0, y0, radius, num_points=4):
    """
    Samples the primary beams to determine the tiles.

    x0, y0    :  beam center in degrees.
    radius    :  the beam radius.
    num_points: is a number of sample points within a circular beam.

    """
    angle = numpy.linspace(0, 360, num_points)
    angle = numpy.deg2rad(angle)

    if isinstance(x0, list):
        ra_corners = []
        dec_corners = []
        for x_0, y_0 in zip(x0, y0):
            declination = radius * numpy.sin(angle) + y_0
            dec_corners.append(declination)
            ra_corners.append(
                (radius * numpy.cos(angle)) / numpy.cos(numpy.deg2rad(declination))
                + x_0
            )

    else:
        dec_corners = radius * numpy.sin(angle) + y0
        ra_corners = (radius * numpy.cos(angle)) / numpy.cos(
            numpy.deg2rad(dec_corners)
        ) + x0

    ra_corners = numpy.asarray(ra_corners)
    dec_corners = numpy.asarray(dec_corners)

    ra_corners = ra_corners.flatten()
    dec_corners = dec_corners.flatten()

    return ra_corners, dec_corners


def get_healpix_tiles(ra_deg, dec_deg):
    """Determines healpix tiles for the beam sampled points"""

    SB_index = hp.lonlat_to_healpix(
        ra_deg * u.deg, dec_deg * u.deg, return_offsets=False
    )
    SB_index_unique = numpy.unique(SB_index)
    return SB_index_unique


def generate_DS9_polygons(healpix_pixel, nside, outname_prefix):
    """
    Option function: for the extracted tiles, it generates the
    ds9 region files.
    """

    regions = []
    centers = []
    texts = []
    for pixel in healpix_pixel:
        corner = hp.boundaries_lonlat(pixel, step=1) * u.deg
        RA, DEC = corner.value
        RA = RA[0]
        DEC = DEC[0]
        polygon_string = f"polygon({RA[0]:f}, {DEC[0]:f}, {RA[1]:f}, {DEC[1]:f}, {RA[2]:f}, {DEC[2]:f}, {RA[3]:f}, {DEC[3]:f})"
        regions.append(polygon_string)

        center = hp.healpix_to_lonlat(pixel) * u.deg
        center_RA, center_DEC = center.value

        circle_string = f"circle({center_RA:f}, {center_DEC:f}, {0.1:f})"
        centers.append(circle_string)

        text_string = f"text {center_RA} {center_DEC} {{{pixel}}}"
        texts.append(text_string)

    first_line = "#Region file format: DS9 version 4.1 \n"
    second_line = (
        'global color=black dashlist=8 3 width=2 font="helvetica 10 normal roman" \
    select=1 highlite=1 dash=0 fixed=0 edit=1 move=1 delete=1 include=1 source=1 \n'
    )
    third_line = "fk5 \n"
    SB = outname_prefix

    # boundary region file
    with open(f"{SB}-boundary-{nside}.reg", "w") as region_file:
        region_file.write(first_line)
        region_file.write(second_line)
        region_file.write(third_line)
        region_file.writelines(region + " \n" for region in regions)

    # centers region file
    with open(f"{SB}-center-{nside}.reg", "w") as center_file:
        center_file.write(first_line)
        center_file.write(second_line)
        center_file.write(third_line)
        for center in centers:
            center_file.write(center + " \n")

    # text region file
    with open(f"{SB}-text-{nside}.reg", "w") as text_file:
        text_file.write(first_line)
        text_file.write(second_line)
        text_file.write(third_line)
        text_file.writelines(text + " \n" for text in texts)


def reference_header(naxis, cdelt):
    """
    Reference header centred at (0, 0) in a healpix grid.
    This is important as it allows us to properly determine
    correct pixel central pixel anywhere within the grid.

    cdelt : the pixel size of the image in the grid. Must be the
            same as the one used for tiling.
    naxis : number of pixels within each axis.

    """

    hdr = "SIMPLE  =                    T / file does conform to FITS standard \n"
    hdr += "BITPIX  =                  -32 / number of bits per data pixel \n"
    hdr += "NAXIS   =                    2 / number of data axes  \n"
    hdr += f"NAXIS1  =                {naxis} / length of data axis 1 \n"
    hdr += f"NAXIS2  =                {naxis} / length of data axis 2 \n"
    hdr += "EXTEND  =                    F / No FITS extensions are present \n"
    # NOTE: update adding 0.5 to CRPIX 1/2 to fix [2049, 2049, X, X] shape error
    hdr += "CRPIX1  =             %r / Coordinate reference pixel \n" % (
        (naxis / 2.0) + 0.5
    )
    hdr += "CRPIX2  =             %r / Coordinate reference pixel \n" % (
        (naxis / 2.0) + 0.5
    )
    hdr += "PC1_1   =           0.70710677 / Transformation matrix element \n"
    hdr += "PC1_2   =           0.70710677 / Transformation matrix element \n"
    hdr += "PC2_1   =           -0.70710677 / Transformation matrix element \n"
    hdr += "PC2_2   =           0.70710677 / Transformation matrix element \n"
    hdr += f"CDELT1  =            -{cdelt!r}  / [deg] Coordinate increment \n"
    hdr += f"CDELT2  =             {cdelt!r}  / [deg] Coordinate increment \n"
    hdr += "CTYPE1  = 'RA---HPX'           / Right ascension in an HPX projection \n"
    hdr += "CTYPE2  = 'DEC--HPX'           / Declination in an HPX projection \n"
    hdr += "CRVAL1  =                   0. / [deg] Right ascension at the reference point \n"
    hdr += (
        "CRVAL2  =                   0. / [deg] Declination at the reference point \n"
    )
    hdr += "PV2_1   =                    4 / HPX H parameter (longitude) \n"
    hdr += "PV2_2   =                    3 / HPX K parameter  (latitude) \n"

    return hdr


def tile_number_to_tile_parameters(Nside, hpx_ids, tile_size, hpx_wcs):
    """Determine the cutout parameters (CRPIX1, CRPIX2) for
    a POSSUM tile (an HPX pixel of order 32).

    Returns CRPIX1, CRPIX2, CRVAL1, CRVAL2 (tuple of 4 floats)
    """
    CRPIX1 = []
    CRPIX2 = []
    CRVAL1 = []
    CRVAL2 = []

    for hpx_tile_num in hpx_ids:
        lon, lat = hp.healpix_to_lonlat(hpx_tile_num) * u.deg
        x, y = hpx_wcs.wcs_world2pix(lon, lat, 0)

        # NOTE: required correction for all edge tiling for all packages
        CRPIX1.append(numpy.round(-1 * x + tile_size, 5).astype("float"))
        CRPIX2.append(numpy.round(-1 * y + tile_size, 5).astype("float"))
        CRVAL1.append(lon.value)
        CRVAL2.append(lat.value)

    return CRPIX1, CRPIX2, CRVAL1, CRVAL2


def parse_args(argv):
    parser = argparse.ArgumentParser("Generate files defining Healpix tiles.")
    parser.add_argument("-f", dest="file", help="Footprint file", required=True)
    parser.add_argument("-o", dest="output", help="Output file prefix", required=True)
    parser.add_argument(
        "-i", dest="id", help="Observation ID for output file", required=True
    )
    parser.add_argument(
        "-j",
        dest="json",
        help="The healpix tile configuration file [json].",
        required=True,
    )
    parser.add_argument(
        "-r",
        dest="regions",
        action="store_true",
        help="Generate DS9 regions",
        default=False,
        required=False,
    )

    # optional
    parser.add_argument(
        "-p",
        dest="prefix",
        type=str,
        help="Prefix for output tile filenames",
        required=False,
        default="hpx_pixel_map",
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    args = parse_args(argv)
    logger.info(args)

    # if not os.path.exists(args.output):
    try:
        os.makedirs(args.output, exist_ok=True)
    except FileExistsError:
        pass

    # read config
    if not os.path.exists(args.json):
        raise Exception(f"Healpix tile configuration file not found at {args.json}")
    with open(args.json, "r") as f:
        tile_config = json.load(f)

    footprint = args.file
    if not os.path.exists(footprint):
        raise Exception(f"Footprint file not found at {footprint}")
    logger.info(f"Footprint file: {footprint}")

    # healpix tile configuration and beam information
    nside = tile_config["nside"]
    beam_radius = tile_config["beam_radius"]
    beam_sample_points = tile_config["beam_sample_points"]
    naxis = tile_config["tile_naxis"]
    cdelt = tile_config["tile_cdelt"]
    number_of_beams = tile_config["number_of_beams"]

    # globalizing Healpix definition.
    global hp
    hp = HEALPix(nside=nside, order="ring", frame="icrs")

    logger.info(f"Number of pixels for nside {nside} is {hp.npix}. ")
    logger.info(
        f"HealPix pixel resolution for nside {nside} is {hp.pixel_resolution}."
    )

    hpx_id_pixels = {}
    hpx_pixels = []
    footprint_ids = []

    footprint_id = args.id
    extension = footprint.rsplit(".", 1)[1]
    if extension == "reg":
        footprint_region = pyregion.open(footprint)
        x_deg = [r.coord_list[0] for r in footprint_region]
        y_deg = [r.coord_list[1] for r in footprint_region]
    elif extension == "txt":
        footprint_region = pd.read_csv(footprint, header=None, sep=")")
        x_deg = [footprint_region[1][i].split(",")[0] for i in range(number_of_beams)]
        y_deg = [footprint_region[1][i].split(",")[1] for i in range(number_of_beams)]
        x_deg, y_deg = get_deg(x_deg, y_deg)
    else:
        raise Exception(f"Unexpected extension for footprint file {footprint}")

    beam_x_corner_sample, beam_y_corner_sample = points_within_circle(
        x_deg, y_deg, beam_radius, num_points=beam_sample_points
    )
    healpixels = get_healpix_tiles(
        ra_deg=beam_x_corner_sample, dec_deg=beam_y_corner_sample
    )
    hpx_pixels.append(healpixels)
    footprint_ids.append(footprint_id)
    hpx_id_pixels.update({f"{footprint_id}": healpixels})

    # read the reference header to estimate pixel centers in degrees, J2000.
    HPX_hdr = reference_header(naxis=naxis, cdelt=cdelt)
    HPX_hdr = fits.Header.fromstring(f"""{HPX_hdr}""", sep="\n")
    HPX_wcs = WCS(HPX_hdr)
    crpix_ra, crpix_dec, hpx_ra, hpx_dec = tile_number_to_tile_parameters(
        Nside=nside, hpx_ids=hpx_pixels, tile_size=naxis, hpx_wcs=HPX_wcs
    )

    # TODO: loop not necessary
    # iterate over pixels to write pixel map
    for i in range(len(footprint_ids)):
        csv_filename = f"{args.prefix}_{footprint_id}.csv"
        csv_tile_output = os.path.join(args.output, csv_filename)
        logger.info(f"Writing pixel map to {csv_tile_output}")
        with open(csv_tile_output, "w", newline="") as f:
            writer = csv.writer(f)
            data = [
                tuple(hpx_pixels[i].tolist()),
                tuple(crpix_ra[i].tolist()),
                tuple(crpix_dec[i].tolist()),
                tuple(hpx_ra[i].tolist()),
                tuple(hpx_dec[i].tolist()),
            ]
            data_zip = zip(*data)
            csv_header = [
                "PIXELS",
                "CRPIX_RA",
                "CRPIX_DEC",
                "CRVAL_RA [deg]",
                "CRVAL_DEC [deg]",
            ]
            writer.writerow(csv_header)
            writer.writerows(data_zip)

    HPX_PIXELS = numpy.unique(numpy.hstack(hpx_pixels))  # all HPX tiles.

    SBsID = []
    SBs_HPX = []
    for hpxs in HPX_PIXELS:
        for SBid in footprint_ids:
            if hpxs in set(hpx_id_pixels[SBid]):
                SBs_HPX.append(hpxs)
                SBsID.append(SBid)

    csv_repeat_tiles = args.output + "_REPEAT.csv"
    with open(csv_repeat_tiles, "w", newline="") as f:
        writer = csv.writer(f)
        data = []
        j = 0
        for hpx in numpy.unique(SBs_HPX):
            count = SBs_HPX.count(hpx)

            if count == 1:
                j += 1

            if count >= 2:
                ind = numpy.where(hpx == SBs_HPX)[0].tolist()
                SBs_data = numpy.asarray(SBsID)[ind]
                SBs_temp = SBs_data.tolist()
                data.append(numpy.hstack([hpx, SBs_temp]).tolist())

        if data:
            maximum_number_SBs = max([len(n) for n in data])
            csv_header = numpy.hstack(
                ["PIXEL", [f"SB{i}" for i in range(1, maximum_number_SBs)]]
            ).tolist()
            writer.writerow(csv_header)
            writer.writerows(data)
        else:
            # delete
            if os.path.exists(csv_repeat_tiles):
                os.remove(csv_repeat_tiles)

    if args.regions:
        logger.info("Writing DS9 region files")
        generate_DS9_polygons(
            healpix_pixel=HPX_PIXELS,
            nside=nside,
            outname_prefix=os.path.join(args.output, args.prefix),
        )

    print(footprint_id, end="")


if __name__ == "__main__":
    main(sys.argv[1:])
