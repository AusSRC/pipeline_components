#!/usr/bin/env python3

"""
Code to identify which healpix tiles to mosaic for each incoming observation.
This code is run once for each new observation.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import numpy as np
import pandas as pd


logging.basicConfig(level=logging.INFO)


def get_obs_id_from_filename(filename):
    """Function to extract the unique identifier from the HPX tile fits files.
    Remove prefix.

    """
    return filename.split('_')[-1].split('.')[0].rsplit('-', 1)[0]


def get_hpx_tile_from_filename(filename):
    """Get the HPX tile ID from filename

    """
    return int(filename.split('-')[-1].split('.')[0])


def main(argv):
    # Arguments
    parser = argparse.ArgumentParser('Determine whether new tile can be completed for a given observation.')
    parser.add_argument('-f', dest='files', help='Directory where tiling files are stored', required=True)
    parser.add_argument(
        '-m', dest='tile_map', help='Map from HPX pixels to the required observation ids', required=True
    )
    args = parser.parse_args(argv)

    if not os.path.exists(args.files):
        raise Exception(f'Healpix tile directory {args.files} does not exist')

    # Read
    tiles_df = pd.read_csv(args.tile_map)
    tiles_df = tiles_df.replace({np.nan: None})
    logging.info(f'Map: {tiles_df}')

    # Get files and previously observed obs_ids
    files = list(Path(args.files).rglob('*.fits'))
    logging.info(f'Files in specified directory: {files}')
    observed_pixels = {}
    pixels_to_files = {}
    for f in files:
        pixel_id = get_hpx_tile_from_filename(f.name)
        obs_id = get_obs_id_from_filename(f.name)
        if pixel_id in observed_pixels:
            observed_pixels[pixel_id].append(obs_id)
            pixels_to_files[pixel_id].append(str(f))
        else:
            observed_pixels[pixel_id] = [obs_id]
            pixels_to_files[pixel_id] = [str(f)]
    logging.info(f'Completed observation ids: {observed_pixels}')

    # Determine which pixels can be completed
    mosaic_files = []
    for idx, row in tiles_df.iterrows():
        hpx_pixel_id = row.values[0]
        ids = set([v for v in row.values[1:] if v is not None])
        for k, v in observed_pixels.items():
            if (k == hpx_pixel_id) and (ids == set(v)):
                logging.info(f'All observations required for HPX pixel {hpx_pixel_id} are completed.')
                logging.info(f'Can mosaic files {pixels_to_files[k]}')
                mosaic_files.append(pixels_to_files[k])

    mosaic_files_print = [f"[{' '.join(f)}]" for f in mosaic_files]
    print(mosaic_files_print, end='')


if __name__ == '__main__':
    main(sys.argv[1:])
