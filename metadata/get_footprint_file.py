#!/usr/bin/env python3

import os
import sys
import glob
import tarfile
import argparse
import logging


logging.basicConfig(level=logging.ERROR)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p',
        '--path',
        type=str,
        required=True,
        help='Path to directory containing evaluation files.'
    )
    parser.add_argument(
        '-f',
        '--file',
        type=str,
        required=False,
        help='File (or keyword in file) for compressed metadata file',
        default='calibration-metadata-processing-logs'
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
    """Search and retrieve a file from a compressed folder in a specified path.
    Extracts folder and returns full path to file.

        1.  Find the compressed tar file with the --file argument in the path specified by --path.
            This path and compressed file should contain the target file.
        2.  Extract contents from compressed file
        3.  Search for file with the --keyword argument and print first match to stdout.

    """
    args = parse_args(argv)
    if not os.path.exists(args.path):
        raise Exception(f'Path to files {args.path} does not exist.')
    logging.info(f'Looking for footprint files in path "{args.path}" with keyword "{args.file}"')

    footprint = None
    filelist = glob.glob(f'{args.path}/*{args.file}*')
    tarfiles = [f for f in filelist if (('checksum' not in f) and ('.tar' in f))]
    logging.info(f'Compressed files: {tarfiles}')
    for tf in tarfiles:
        with tarfile.open(tf) as tar:
            logging.info(tf)
            files = [ti.name for ti in tar.getmembers() if args.keyword in ti.name]
            if files:
                footprint = files[0]

            logging.info(f'Extracting tar file at {tf}')
            tar.extractall()
            logging.info(f'Searching for "{args.keyword}" in files: {files}')
        if footprint:
            break

    if not footprint:
        raise Exception('No footprint files found in the evaluation files.')

    # Check footprint file exists as expected
    footprint_file = os.path.join(args.path, footprint)
    os.path.exists(footprint_file)
    print(footprint_file, end='')
    return


if __name__ == '__main__':
    main(sys.argv[1:])
