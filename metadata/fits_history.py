#!/usr/bin/env python3

"""
Update the header cards of all of the input fits files with the values provided.
Used to bulk update the files with provenance information.
"""

import os
import sys
import logging
import asyncio
from astropy.io import fits
from argparse import ArgumentParser


logging.basicConfig(level=logging.INFO)


async def add_history_to_fits_header(file, index, history):
    with fits.open(file, mode='update') as hdul:
        header = hdul[index].header
        for value in history:
            header.add_history(value)
        logging.info(f'Updated file {file} completed')
    return


async def main(argv):
    parser = ArgumentParser()
    parser.add_argument("-f", dest="files", nargs="+", help="List of fits files (space separated)")
    parser.add_argument("-i", dest="index", type=int, help="Index of the target ImageHDU in the fits file", default=0)
    parser.add_argument("-v", dest="values", nargs="+", help="Values to add to FITS header HISTORY cards (space separated)", required=False)
    args = parser.parse_args(argv)

    logging.info(f'Adding the following history cards: {args.values}')
    for f in args.files:
        if not os.path.exists(f):
            logging.warning(f'Skipping {f}: file not found')
            continue
        logging.info(f'Updating file {f}')
        await add_history_to_fits_header(f, args.index, args.values)


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
