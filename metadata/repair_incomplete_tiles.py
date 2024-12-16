#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

repair_incomplete_tiles:
A script to check if a partial tile is missing any channels, and to add those
missing channels as NaNs. Intended to be added to the AusSRC pipeline.


Created on Mon Oct 30 14:05:17 2023
@author: cvaneck
"""

import argparse
import glob
import astropy.io.fits as pf
import numpy as np
import os
from pathlib import Path

def command_line():
    """Function for calling from the command line. Takes input directory, optional
    output filename or overwrite order.
    """

    descStr = """
    Check all FITS cubes in a directory to see if it is missing any channels.
    Band 1 tiles should have 288 channels, while band 2 tiles should have 144.

    If the tile is found to be missing channels, a warning will be printed to
    terminal. If the overwrite flag is set, the existing (input) file will be
    replaced by one with all the channels; otherwise the file is left as-is.

    New channels are filled completely with NaNs.

    If the tile is found to have the correct number of channels, nothing is done.
    """

    parser = argparse.ArgumentParser(description=descStr,
                                 formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("directory",metavar="directory",
                        help="Input directory containing partial tile FITS cubes.")
    parser.add_argument("--overwrite",dest="overwrite",action="store_true",
                        help="Update/overwrite existing files.")
    args = parser.parse_args()


    for path in Path(args.directory).rglob('*.fits'):
        file = path.resolve()
        present_channels,expected_channels=check_file(file)
        print(file, present_channels == expected_channels, args.overwrite)
        if (present_channels != expected_channels) and (args.overwrite is True):
            repair_and_write(file,expected_channels, args.overwrite)

def check_file(file):
    """Check if the specified file contains the expected number of channels.
    Warn if not. Returns number of chanels in the cube, and the expected number.

    """
    header = pf.getheader(file)

    if header['CTYPE3'] == 'FREQ':
        freq_header_card = 'CRVAL3'
        present_channels = header['NAXIS3']
    elif header['CTYPE4'] == 'FREQ':
        freq_header_card = 'CRVAL4'
        present_channels = header['NAXIS4']
    else:
        raise Exception('Cube frequency axis is neither CTYPE3 or CTYPE4. Aborting.')

    if np.abs(header[freq_header_card] - 800e6) < 5e6:  # Band 1:
        expected_channels=288
    elif np.abs(header[freq_header_card] - 1296e6) < 5e6:
        expected_channels=144
    else:
        raise Exception('Tile does not start at expected frequencies for Band 1 or 2. Aborting check.')

    if present_channels != expected_channels:
        print(f'File {file} does not have the expected number of channels.')
        print(f'Expected {expected_channels} channels, got {present_channels}.')

    return present_channels, expected_channels


def repair_and_write(file,expected_channels,out=None,overwrite=False):
    """Write a file with the correct number of channels. If overwrite = True
    overwrite/update existing file.

    """
    hdu_list=pf.open(file,mode='append')

    data=hdu_list[0].data
    header=hdu_list[0].header
    header['HISTORY']='Added missing channels full of NaNs using repair_incomplete_tiles.py.'

    #Initialize new array with NaNs
    shape=list(data.shape)
    shape[0]=expected_channels
    new_data=np.zeros(shape,dtype='float32')
    new_data[:]=np.nan

    #Deposit new data. Implicitly assumes to start at bottom channel, and
    #NaN-pad the top channels.
    new_data[0:data.shape[0]]=data

    pf.update(file,new_data,header,ext=0)
    hdu_list.close()



if __name__ == '__main__':
    command_line()


