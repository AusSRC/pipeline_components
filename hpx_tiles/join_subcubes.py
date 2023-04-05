#!/usr/bin/env python3

import os
import sys
import logging
import argparse
import numpy as np
from astropy.io import fits


logging.basicConfig(level=logging.INFO)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f", dest="files", nargs="+", help="Files to join in frequency.", required=True
    )
    parser.add_argument(
        "-o",
        dest="output",
        help="Output filename and path for joined fits file",
        required=True,
    )
    parser.add_argument(
        "-a",
        dest="axis",
        type=int,
        help="Frequency axis index in split fits files",
        default=1,
    )
    parser.add_argument(
        "--overwrite", dest="overwrite", action="store_true", default=False
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Join image cube along frequency axis.

    Usage:
        python join_subcubes.py -f <files> -o <output_filename> -a <freq_axis>

    """
    data = None
    args = parse_args(argv)
    files = args.files

    path = os.path.dirname(args.output)
    try:
        os.makedirs(path)
    except FileExistsError:
        pass

    # NOTE: Order of files here determines how they are joined...
    files.sort()
    logging.info(f"Joining fits files: {files}")
    for f in files:
        if not os.path.exists(f):
            raise Exception(f"Sub-cube file at {files} not found.")
        size = os.path.getsize(f)
        filename = os.path.basename(f)
        logging.info(f"Sub-cube {filename} size: {size / 1E9} GB")
        with fits.open(f) as hdul:
            if data is None:
                header = hdul[0].header
                logging.info(
                    f"{header['CTYPE1']}, {header['CTYPE2']}, {header['CTYPE3']}, {header['CTYPE4']}"
                )
                data = hdul[0].data
            else:
                data = np.concatenate((data, hdul[0].data), axis=args.axis)
            logging.info(f"Output data shape: {data.shape}")

    hdu = fits.PrimaryHDU(header=header, data=data)
    hdul = fits.HDUList([hdu])
    hdul.writeto(args.output, overwrite=args.overwrite)


if __name__ == "__main__":
    argv = sys.argv[1:]
    main(argv)
