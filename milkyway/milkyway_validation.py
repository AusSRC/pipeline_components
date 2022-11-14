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
    logging.info('Creating moment map')
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


async def calculate_rms(image_filename, name, cube, output):
    logging.info('Calculating RMS')
    loop = asyncio.get_running_loop()
    askap = await loop.run_in_executor(None, partial(
        fits.open,
        image_filename
    ))
    d_askap = askap[0].data
    # h_askap = askap[0].header
    # w_askap = WCS(h_askap, askap)

    # calculate per channel properties of the cube
    # this section takes the longest
    # this section could probably be optimized

    rms = []
    min_a = []
    max_a = []

    for i in range(cube.shape[0]):
        slice = d_askap[i, 0, :, :]
        if np.isnan(slice).all():
            # TODO: what to add when NaN values present?
            rms.append(np.nan)
            min_a.append(np.nan)
            max_a.append(np.nan)
        else:
            rms.append(np.sqrt(np.nanmean(np.square(slice))))
            min_a.append(np.nanmin(slice))
            max_a.append(np.nanmax(slice))

    logging.info(f'RMS: {rms}')

    restfreq = 1.420405752 * u.GHz  # rest frequency of HI
    freq_to_vel = u.doppler_optical(restfreq)  # using the radio convention
    vel_askap = (cube.spectral_axis).to(u.km / u.s, equivalencies=freq_to_vel)
    vel_askap_values = [v.value for v in vel_askap]

    # write per channel rms into csv file
    df_spectra = pd.DataFrame()
    df_spectra['velocity'] = vel_askap_values
    df_spectra['rms'] = rms
    df_spectra['min'] = min_a
    df_spectra['max'] = max_a
    df_spectra.to_csv('./{}_rms_spectrum.txt'.format(name), sep='\t')

    # make plots of the cube properties
    fig = plt.figure(figsize=(16, 12))
    ax1 = fig.add_subplot(111)
    plt.title('{} rms'.format(name), fontsize=25)
    # plt.plot(vel_askap[:-35],rms[:-35], lw=3)
    plt.plot(vel_askap[:-12], rms[:-12], lw=3)
    plt.grid(linestyle=':')
    plt.ylabel('Flux [Jy/beam]', fontsize=28)
    plt.xlabel("velocity [km/s]", fontsize=28)
    # plt.xlim(0,235)
    rms_av = np.average(rms[6:-35])
    print('average rms:', rms_av)
    # rms_max = np.max(rms)
    # plt.ylim(rms_av-0.0003, rms_max+0.0001)
    ax1.tick_params(axis='both', which='major', labelsize=25)
    rms_figure = os.path.join(output, f'{name}_rms.png')
    fig.savefig(rms_figure)

    fig = plt.figure(figsize=(16, 12))
    ax1 = fig.add_subplot(111)
    plt.title('{} min, max'.format(name), fontsize=25)
    # plt.plot(vel_askap[:-35],min_a[:-35], lw=3)
    # plt.plot(vel_askap[:-35],max_a[:-35], lw=3)
    plt.plot(vel_askap[:-12], min_a[:-12], lw=3)
    plt.plot(vel_askap[:-12], max_a[:-12], lw=3)
    plt.grid(linestyle=':')
    plt.ylabel('Flux [Jy/beam]', fontsize=28)
    plt.xlabel("velocity [km/s]", fontsize=28)
    # plt.xlim(0,235)
    min_av = np.average(min_a[6:-35])
    max_av = np.average(max_a[6:-35])
    print('average min, max:', min_av, max_av)
    # rms_max = np.max(rms)
    # plt.ylim(rms_av-0.0001, rms_max+0.0001)
    ax1.tick_params(axis='both', which='major', labelsize=25)

    min_max_figure = os.path.join(output, f'{name}_min_max.png')
    fig.savefig(min_max_figure)

    # write a file with the average rms, min, max values
    average_values_file = os.path.join(output, f'{name}_average_values.txt')
    with open(average_values_file, 'w') as f:
        f.write('average rms: {} \n'.format(rms_av))
        f.write('average min, max: {}, {}'.format(min_av, max_av))


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
    await calculate_rms(args.input, args.name, cube, output_dir)


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
