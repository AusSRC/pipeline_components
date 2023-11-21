#!/usr/bin/env python3

import os
import sys
import glob
import tarfile
import argparse
import logging
from pathlib import Path


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        required=True,
        help="Path to directory containing evaluation files.",)
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        required=True,
        help="File (or keyword in file) for compressed metadata file",
        default="calibration-metadata-processing-logs",)
    parser.add_argument(
        "-k",
        "--keyword",
        type=str,
        required=True,
        help="Search key word for identifying file of interest",
        default="metadata/footprintOutput",)
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Output directory",
        default="metadata",)

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
    filename = None

    args = parse_args(argv)
    if not os.path.exists(args.path):
        raise Exception(f"Path to files {args.path} does not exist.")

    filelist = glob.glob(f"{args.path}/*{args.file}*")
    if not filelist:
        # scan the input directory for the existing file
        keyfile = None
        for f in glob.glob(f"{args.path}/**/{os.path.basename(args.keyword)}*", recursive=True):
            if os.path.islink(f):
                continue
            else:
                print(f, end="")
                return

        if keyfile is None:
            raise Exception(f"No files found in {args.path} with compressed file matching {args.file}")

    tarfiles = [f for f in filelist if (("checksum" not in f) and (".tar" in f))]
    if not tarfiles:
        raise Exception(f"No compressed files found in {args.path} with filename matching {args.file}")

    for tf in tarfiles:
        with tarfile.open(tf) as tar:
            for member in tar.getmembers():
                if member.isdir():
                    continue
                if args.keyword in member.name:
                    member.name = os.path.basename(member.name)
                    try:
                        tar.extract(member, args.output)
                    except Exception as e:
                        continue
                    full_path = f"{args.output}/{member.name}"
                    if os.path.islink(full_path):
                        continue
                    else:
                        filename = full_path

    if not os.path.exists(filename):
        raise Exception(f"No file found {filename}")

    print(filename, end="")

if __name__ == "__main__":
    main(sys.argv[1:])
