#!/usr/bin/env python3

"""
Update the header cards of all of the input fits files with the values provided.
Used to bulk update the files with provenance information.
"""

import asyncio
import logging
import os
import sys
from argparse import ArgumentParser

from astropy.io import fits

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_history_to_fits_header(file, index, history):
    with fits.open(file, mode="update") as hdul:
        header = hdul[index].header
        for value in history:
            header.add_history(value)
        logger.info(f"Updated file {file} completed")


async def main(argv):
    parser = ArgumentParser()
    parser.add_argument(
        "-f", dest="files", nargs="+", help="List of fits files (space separated)"
    )
    parser.add_argument(
        "-i",
        dest="index",
        type=int,
        help="Index of the target ImageHDU in the fits file",
        default=0,
    )
    parser.add_argument(
        "-v",
        dest="values",
        nargs="+",
        help="Values to add to FITS header HISTORY cards (space separated)",
        required=False,
    )
    args = parser.parse_args(argv)

    logger.info(f"Adding the following history cards: {args.values}")
    for f in args.files:
        if not os.path.exists(f):
            logger.warning(f"Skipping {f}: file not found")
            continue
        logger.info(f"Updating file {f}")
        await add_history_to_fits_header(f, args.index, args.values)


if __name__ == "__main__":
    argv = sys.argv[1:]
    asyncio.run(main(argv))
