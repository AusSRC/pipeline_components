#!/usr/bin/env python3

import os
import sys
import glob
import tarfile
import argparse
import logging
from pathlib import Path


logging.basicConfig(level=logging.INFO)


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
        help='Search key word for identifying file of interest',
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
    logging.info(f'Looking for files in path "{args.path}" with filename matching "{args.file}"')

    filename = None

    filelist = glob.glob(f'{args.path}/*{args.file}*')
    if not filelist:
        raise Exception(f'No files found in {args.path} with compressed file matching {args.file}')

    tarfiles = [f for f in filelist if (('checksum' not in f) and ('.tar' in f))]
    if not tarfiles:
        raise Exception(f'No compressed files found in {args.path} with filename matching {args.file}')

    logging.info(f'Compressed files: {tarfiles}')
    for tf in tarfiles:
        with tarfile.open(tf) as tar:
            logging.info(tf)
            files = [ti.name for ti in tar.getmembers() if args.keyword in ti.name]
            dirs = list(set([Path(os.path.join(args.path, f)).parent.absolute() for f in files]))
            for d in dirs:
                logging.info(f'Looking in directory {d}')
                # If directory already exists do not extract from compressed file
                if not os.path.exists(d):
                    logging.info(f'Extracting tar file at {tf}')
                    tar.extractall(path=args.path)

                # Find file that is not symlink
                match_files = [f for f in glob.glob(str(d) + '/*') if args.keyword in f]
                for f in match_files:
                    if not os.path.islink(f):
                        match_file = f
                        filename = os.path.join(args.path, match_file)
                        break
                if filename:
                    break
        if filename:
            break

    if not match_file:
        raise Exception('No footprint files found in the evaluation files.')
    if not os.path.exists(filename):
        raise Exception(f'No file found {filename}')
    print(filename, end='')
    return


if __name__ == '__main__':
    main(sys.argv[1:])
