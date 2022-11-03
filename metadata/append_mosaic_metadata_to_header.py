#!/usr/bin/env python3

"""
Add metadata about linmos run to the fits header.
"""

import os
import sys
import logging
import argparse
from astropy.io import fits


logging.basicConfig(level=logging.INFO)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', dest='image_cubes', nargs='+', help='Image cube files to add metadata to.')
    parser.add_argument('-s', dest='sbids', nargs='+', help='SBIDs to add to the header')
    parser.add_argument('-c', dest='config', help='Linmos configuration')
    args = parser.parse_args(argv)
    logging.info(args)
    logging.info(f'Adding SBIDs to header: {args.sbids}')

    # Checks
    if not os.path.exists(args.config):
        raise Exception(f'Linmos config not found at {args.config}')
    with open(args.config) as f:
        lines = [l.replace(' ', '').strip('\n') for l in f.readlines()]
    for f in args.image_cubes:
        if not os.path.exists(f):
            raise Exception(f'Image cube file could not be found {f}')

    # Add to header
    logging.info(f'Adding linmos config ({args.config}) to header')
    logging.info(lines)
    for f in args.image_cubes:
        with fits.open(f, mode='update') as hdu:
            hdr = hdu[0].header

            # add sbids
            for sbid in args.sbids:
                hdr.append(('SBID', sbid, 'SBID of mosaicked observation'), end=True)
            for l in lines:
                hdr['HISTORY'] = l


if __name__ == '__main__':
    main(sys.argv[1:])