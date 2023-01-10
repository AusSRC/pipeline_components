#!/usr/bin/env python3

"""
Add constituent SBIDs to the fits header of mosaicked cubes.
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
    parser.add_argument('-s', dest='sbids', nargs='+', help='SBIDs to add to the header', required=False)
    args = parser.parse_args(argv)
    logging.info(args)
    logging.info(f'Adding SBIDs to header: {args.sbids}')

    # Check for existing SBIDs
    sbid_list = []
    for f in args.image_cubes:
        if not os.path.exists(f):
            raise Exception(f'Image cube file could not be found {f}')
        # Check if SBIDs in header
        with fits.open(f, mode='readonly') as hdu:
            hdr = hdu[0].header
            if 'SBID' in hdr.keys():
                sbids_str = hdr['SBID']
                sbid_list += sbids_str.split(' ')

    logging.info(f'Also adding SBIDs from existing image cubes {list(set(sbid_list))} to header')
    if args.sbids:
        sbid_set = list(set(sbid_list + args.sbids))
    else:
        sbid_set = list(set(sbid_list))

    # Add to header
    logging.info(f'Updated SBID card in header: {" ".join(sbid_set)}')
    # TODO(austin): If longer than 80 characters will need to split
    for f in args.image_cubes:
        with fits.open(f, mode='update') as hdu:
            hdr = hdu[0].header
            sbids = ' '.join(sbid_set)
            hdr['SBID'] = sbids


if __name__ == '__main__':
    main(sys.argv[1:])
