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
        "-f", dest="files", nargs="+", help="Files to join in frequency.", required=True)
    parser.add_argument(
        "-o",
        dest="output",
        help="Output filename and path for joined fits file",
        required=True,)
    parser.add_argument(
        "-a",
        dest="axis",
        type=str,
        help="Fits header CTYPE axis on which to join",
        default='FREQ',
        required=False)
    parser.add_argument(
        "--overwrite", dest="overwrite", action="store_true", default=False)
    args = parser.parse_args(argv)
    return args


# Assume filename is split_chan1-chan2_*
def split_key(s):
    a = s.split('split_')[1].split('-')[0]
    return int(a)


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
        os.makedirs(path, exist_ok=True)
    except FileExistsError:
        pass

    # NOTE: Order of files here determines how they are joined...
    files.sort(key=split_key)
    logging.info(f"Joining fits files: {files}")
    logging.info(f'Joining on axis {args.axis}')

    # Check axis that contains CTYPE defined by user argument.
    # NOTE: assumes all files have the same axis order
    axis = None
    with fits.open(files[0]) as hdul:
        header = hdul[0].header
        naxis = int(header['NAXIS'])
        for i in range(naxis):
            card = str(header[f'CTYPE{str(i+1)}']).strip()
            if card == args.axis:
                axis = naxis - (i + 1)
                logging.info(f'Joining on data axis {axis} for {args.axis}')
                break
    if axis is None:
        raise Exception(f'Did not find axis in fits header to join on: {args.axis}')

    for f in files:
        if not os.path.exists(f):
            raise Exception(f"Sub-cube file at {files} not found.")
        size = os.path.getsize(f)
        filename = os.path.basename(f)
        logging.info(f"Sub-cube {filename} size: {size / 1E9} GB")
        with fits.open(f) as hdul:
            if data is None:
                header = hdul[0].header
                logging.info(f"{header['CTYPE1']}, {header['CTYPE2']}, {header['CTYPE3']}, {header['CTYPE4']}")
                data = hdul[0].data
            else:
                data = np.concatenate((data, hdul[0].data), axis=axis)
            logging.info(f"Output data shape: {data.shape}")

    # Cast certain header card values to float
    write_header = header.copy()
    prefixes = ['CRPIX', 'CRVAL', 'CDELT']
    for idx in range(naxis):
        for prefix in prefixes:
            card = f'{prefix}{str(idx+1)}'
            write_header.set(card, float(write_header[card]))

    hdu = fits.PrimaryHDU(header=write_header, data=data)
    hdu.writeto(args.output, overwrite=args.overwrite)


if __name__ == "__main__":
    argv = sys.argv[1:]
    main(argv)
