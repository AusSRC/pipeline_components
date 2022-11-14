#!/usr/bin/env python3

import os
import sys
import argparse
import logging
import asyncio
from functools import partial
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from astropy import units as u
from astropy.io import fits
from spectral_cube import SpectralCube
import aplpy
from astropy.wcs import WCS
import pandas as pd
from astroquery.vizier import Vizier
from astroquery.skyview import SkyView
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation

mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.size'] = '16'
mpl.rcParams['xtick.direction'] = 'in'
mpl.rcParams['ytick.direction'] = 'in'
logging.basicConfig(level=logging.INFO)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', dest='name', help='Name of the field/observation for output subdirectory', required=True)
    parser.add_argument('-i', dest='input', help='Input Milkyway image cube', required=True)
    parser.add_argument('-o', dest='output', help='Output write directory for figures', required=True)
    args = parser.parse_args(argv)
    return args


async def make_moment_map(filename, cube, output, vel=[-10, 10]):
    cube_3 = cube.with_spectral_unit(u.km/u.s, velocity_convention='optical', rest_value=1.420405752 * u.GHz)
    subcube = cube_3.spectral_slab(vel[0]*u.km/u.s, vel[1]*u.km/u.s)
    moment_0_v3 = subcube.moment(order=0)

    f = aplpy.FITSFigure(moment_0_v3.hdu)
    f.show_colorscale(cmap='magma')
    f.set_title('{} mom 0 ({}-{} km/s)'.format(filename, vel[0], vel[1]))
    f.add_colorbar()
    f.colorbar.set_axis_label_text('Integrated Intensity (Jy/beam)')
    f.colorbar.set_axis_label_font(size=18)
    f.colorbar.set_font(size=20, weight='medium', family='serif')

    f.axis_labels.set_font(size=20, weight='medium', family='serif')
    f.tick_labels.set_font(size=20, weight='medium', family='serif')
    outname_png = os.path.join(output, f'{filename}_mom_0_{vel[0]}-{vel[1]}.png')
    f.save(outname_png, dpi=200)

    hdul = fits.HDUList([moment_0_v3.hdu])
    hdul[0].header['BMIN'] = 0.5
    hdul[0].header['BMAJ'] = 0.5
    hdul[0].header['BPA'] = 0
    outname_fits = os.path.join(output, f'{filename}_mom_0_{vel[0]}-{vel[1]}kms.fits')
    hdul.writeto(outname_fits, overwrite=True)


async def main(argv):
    loop = asyncio.get_running_loop()
    args = parse_args(argv)

    # setup output directories
    if not os.path.exists(args.output):
        logging.info(f'Creating output directory {args.output}')
        os.mkdir(args.output)
    output_dir = os.path.join(args.output, args.name)
    if not os.path.exists(output_dir):
        logging.info(f'Creating output subdirectory {output_dir}')
        os.mkdir(output_dir)
    filename = os.path.splitext(os.path.basename(args.input))[0]

    # read cube
    cube = await loop.run_in_executor(None, partial(
        SpectralCube.read,
        args.input
    ))
    await make_moment_map(filename, cube, output_dir)


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
