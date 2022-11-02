#!/usr/bin/env python3

"""
Get footprint files for a given SBID.
The footprint file will be retrieved from the evaluation files.
"""

import os
import sys
import glob
import tarfile
import argparse
import logging


logging.basicConfig(level=logging.INFO)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        '--files',
        type=str,
        required=True,
        help='Path to directory containing evaluation files.'
    )
    parser.add_argument(
        '-k',
        '--keyword',
        type=str,
        required=False,
        help='Search key word for identifying footprint files',
        default='metadata/footprintOutput'
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Get the footprint file from evaluation files.
    This code will print the first instance found.

    """
    args = parse_args(argv)
    if not os.path.exists(args.files):
        raise Exception(f'Path to evaluation files {args.files} does not exist.')
    logging.info(f'Looking for footprint files in path "{args.files}" with keyword "{args.keyword}"')

    footprint_file = None
    filelist = glob.glob(f'{args.files}/*')
    logging.info(f'Found the following files: {args.files}')
    tarfiles = [f for f in filelist if (('checksum' not in f) and ('.tar' in f))]
    logging.info(f'Compressed files: {tarfiles}')
    for tf in tarfiles:
        with tarfile.open(tf) as tar:
            logging.info(tf)
            files = [ti.name for ti in tar.getmembers() if args.keyword in ti.name]
            if files:
                footprint_file = files[0]
            logging.info(f'Searching for "{args.keyword}" in files: {files}')

    if not footprint_file:
        raise Exception('No footprint files found in the evaluation files.')
    print(footprint_file)
    return


if __name__ == '__main__':
    main(sys.argv[1:])
