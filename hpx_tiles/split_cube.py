#!/usr/bin/env python3

import os
import sys
import time
import math
import logging
import argparse
from astropy.io import fits
from casatasks import exportfits, imsubimage


logging.basicConfig(level=logging.INFO)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", dest="image", help="Image cube file", required=True)
    parser.add_argument(
        "-o", dest="output", help="Output location for sub-cubes", required=True
    )
    parser.add_argument(
        "-n",
        dest="n_split",
        type=int,
        help="Number of splits to make (along frequency axis",
        required=True,
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Split image cube along frequency axis.

    Usage:
        python split_cube.py -i <image_cube> -o <output_dir> -n <nsplit>

    Returns comma separated filenames of split cubes.

    """
    args = parse_args(argv)
    image = args.image
    if not os.path.exists(image):
        raise Exception(f"Image cube {image} not found.")
    with fits.open(image, memmap=True) as hdu:
        header = hdu[0].header
        n_channels = header["NAXIS4"]

    basename = os.path.basename(image)

    output_dir = args.output
    try:
        os.makedirs(output_dir)
    except FileExistsError:
        pass

    n_split = args.n_split
    n_freq = math.floor(n_channels / n_split)
    logging.info(
        f"Breaking image {image} into {n_split} sub cubes by frequency in {n_freq} channels."
    )

    filenames = []
    for i in range(n_split):
        lower = n_freq * i
        upper = n_freq * (i + 1) - 1
        if (i + 1) == n_split:
            upper = n_channels - 1

        logging.info(f"[{i+1}/{n_split}] Range {lower}-{upper}.")
        start = time.time()
        filename = f"split_{lower}-{upper}_{basename}"
        outimage = os.path.join(output_dir, filename.split(".fits")[0] + ".image")
        fitsimage = os.path.join(output_dir, filename)
        imsubimage(
            imagename=image, outfile=outimage, chans=f"{lower}~{upper}", overwrite=True
        )
        exportfits(imagename=outimage, fitsimage=fitsimage, overwrite=True)
        filenames.append(filename)
        logging.info(
            f"[{i+1}/{n_split}] Split completed in {time.time() - start} seconds"
        )

    filenames_str = ",".join(filenames)
    print(filenames_str, end="")


if __name__ == "__main__":
    argv = sys.argv[1:]
    main(argv)
