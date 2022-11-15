#!/usr/bin/env python3

import os
import sys
import argparse
import logging
import asyncio
import time
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
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation

mpl.rcParams["font.family"] = "serif"
mpl.rcParams["font.size"] = "16"
mpl.rcParams["xtick.direction"] = "in"
mpl.rcParams["ytick.direction"] = "in"
logging.basicConfig(level=logging.INFO)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        dest="name",
        help="Name of the field/observation for output subdirectory",
        required=True,
    )
    parser.add_argument(
        "-i", dest="input", help="Input Milkyway image cube", required=True
    )
    parser.add_argument(
        "-o", dest="output", help="Output write directory for figures", required=True
    )
    args = parser.parse_args(argv)
    return args


async def make_moment_map(filename, cube, output, vel=[-10, 10]):
    start = time.time()
    loop = asyncio.get_running_loop()
    logging.info("Creating moment map")
    cube_3 = cube.with_spectral_unit(
        u.km / u.s, velocity_convention="optical", rest_value=1.420405752 * u.GHz
    )
    subcube = cube_3.spectral_slab(vel[0] * u.km / u.s, vel[1] * u.km / u.s)
    moment_0_v3 = subcube.moment(order=0)

    f = aplpy.FITSFigure(moment_0_v3.hdu)
    f.show_colorscale(cmap="magma")
    f.set_title("{} mom 0 ({}-{} km/s)".format(filename, vel[0], vel[1]))
    f.add_colorbar()
    f.colorbar.set_axis_label_text("Integrated Intensity (Jy/beam)")
    f.colorbar.set_axis_label_font(size=18)
    f.colorbar.set_font(size=20, weight="medium", family="serif")

    f.axis_labels.set_font(size=20, weight="medium", family="serif")
    f.tick_labels.set_font(size=20, weight="medium", family="serif")
    outname_png = os.path.join(output, f"{filename}_mom_0_{vel[0]}-{vel[1]}.png")
    loop.run_in_executor(None, partial(f.save, outname_png, dpi=200))

    hdul = fits.HDUList([moment_0_v3.hdu])
    hdul[0].header["BMIN"] = 0.5
    hdul[0].header["BMAJ"] = 0.5
    hdul[0].header["BPA"] = 0
    outname_fits = os.path.join(output, f"{filename}_mom_0_{vel[0]}-{vel[1]}kms.fits")
    loop.run_in_executor(None, partial(hdul.writeto, outname_fits, overwrite=True))
    end = time.time()
    logging.info(f"Make moment map time {end-start} s")


async def calculate_rms(image_filename, name, cube, output):
    start = time.time()
    logging.info("Calculating RMS")
    loop = asyncio.get_running_loop()
    askap = await loop.run_in_executor(None, partial(fits.open, image_filename))
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
    logging.info(f"RMS: {rms}")

    restfreq = 1.420405752 * u.GHz  # rest frequency of HI
    freq_to_vel = u.doppler_optical(restfreq)  # using the radio convention
    vel_askap = (cube.spectral_axis).to(u.km / u.s, equivalencies=freq_to_vel)
    vel_askap_values = [v.value for v in vel_askap]

    # write per channel rms into csv file
    df_spectra = pd.DataFrame()
    df_spectra["velocity"] = vel_askap_values
    df_spectra["rms"] = rms
    df_spectra["min"] = min_a
    df_spectra["max"] = max_a
    spectrum_file = os.path.join(output, f"{name}_rms_spectrum.txt")
    loop.run_in_executor(None, partial(df_spectra.to_csv, spectrum_file, sep="\t"))

    # make plots of the cube properties
    fig = plt.figure(figsize=(16, 12))
    ax1 = fig.add_subplot(111)
    plt.title("{} rms".format(name), fontsize=25)
    # plt.plot(vel_askap[:-35],rms[:-35], lw=3)
    plt.plot(vel_askap[:-12], rms[:-12], lw=3)
    plt.grid(linestyle=":")
    plt.ylabel("Flux [Jy/beam]", fontsize=28)
    plt.xlabel("velocity [km/s]", fontsize=28)
    # plt.xlim(0,235)
    rms_av = np.average(rms[6:-35])
    logging.info(f"average rms: {rms_av}")
    # rms_max = np.max(rms)
    # plt.ylim(rms_av-0.0003, rms_max+0.0001)
    ax1.tick_params(axis="both", which="major", labelsize=25)
    rms_figure = os.path.join(output, f"{name}_rms.png")
    loop.run_in_executor(None, partial(fig.savefig, rms_figure))

    fig = plt.figure(figsize=(16, 12))
    ax1 = fig.add_subplot(111)
    plt.title("{} min, max".format(name), fontsize=25)
    # plt.plot(vel_askap[:-35],min_a[:-35], lw=3)
    # plt.plot(vel_askap[:-35],max_a[:-35], lw=3)
    plt.plot(vel_askap[:-12], min_a[:-12], lw=3)
    plt.plot(vel_askap[:-12], max_a[:-12], lw=3)
    plt.grid(linestyle=":")
    plt.ylabel("Flux [Jy/beam]", fontsize=28)
    plt.xlabel("velocity [km/s]", fontsize=28)
    # plt.xlim(0,235)
    min_av = np.average(min_a[6:-35])
    max_av = np.average(max_a[6:-35])
    logging.info(f"average min, max: {min_av} {max_av}")
    # rms_max = np.max(rms)
    # plt.ylim(rms_av-0.0001, rms_max+0.0001)
    ax1.tick_params(axis="both", which="major", labelsize=25)

    min_max_figure = os.path.join(output, f"{name}_min_max.png")
    loop.run_in_executor(None, partial(fig.savefig, min_max_figure))

    # write a file with the average rms, min, max values
    average_values_file = os.path.join(output, f"{name}_average_values.txt")
    with open(average_values_file, "w") as f:
        f.write("average rms: {} \n".format(rms_av))
        f.write("average min, max: {}, {}".format(min_av, max_av))

    end = time.time()
    logging.info(f"Calculate rms execution time {end-start} s")


async def calculate_peak_intensity(
    cube, filename, name, output, buffer_1=6, buffer_2=15
):
    start = time.time()
    logging.info("Calculating peak intensity")
    loop = asyncio.get_running_loop()

    cube.allow_huge_operations = True
    cube_2 = cube.unmasked_data[:, :, :]
    # dont use the first few and the last few channels for this
    peak = np.max(cube_2[6: cube_2.shape[0] - 15, :, :], axis=0)

    cube_3 = cube.with_spectral_unit(
        u.km / u.s, velocity_convention="optical", rest_value=1.420405752 * u.GHz
    )
    subcube = cube_3.spectral_slab(-10 * u.km / u.s, 10 * u.km / u.s)
    moment_0_v3 = subcube.moment(order=0)

    hdul = fits.HDUList([moment_0_v3.hdu])
    hdul[0].header["BMIN"] = 0.5
    hdul[0].header["BMAJ"] = 0.5
    hdul[0].header["BPA"] = 0

    im = np.nan_to_num(peak.value)
    wcs = WCS(hdul[0].header)

    # make a figure
    fig = plt.figure(figsize=(16, 12))
    ax = plt.subplot(projection=wcs)
    image = plt.imshow(im, cmap="inferno", vmax=np.percentile(im, 99))

    # ax.set_title('Hydra', fontsize=22)
    ax.tick_params(axis="both", which="major", labelsize=18)
    ax.coords["ra"].set_axislabel("RA (J2000)", fontsize=22)
    ax.coords["dec"].set_axislabel("Dec (J2000)", fontsize=22)
    cbar_hi = plt.colorbar(image, orientation="vertical", fraction=0.022, pad=0.02)
    cbar_hi.set_label("I [Jy]", size=18)

    figure_file = os.path.join(output, f"{name}_peak_intensity.png")
    loop.run_in_executor(
        None, partial(fig.savefig, figure_file, dpi=200, bbox_inches="tight")
    )

    # write the peak intensity map into a fits file
    hdul[0].data = im

    fits_file = os.path.join(output, f"{filename}_peak_intensity.fits")
    loop.run_in_executor(None, partial(hdul.writeto, fits_file, overwrite=True))
    end = time.time()
    logging.info(f"Calculate peak intensity execution time {end-start} s")


async def extract_spectra(cube, output_dir):
    logging.info('Running extract spectra')
    loop = asyncio.get_running_loop()
    start = time.time()
    coordinate = "{} {}".format(cube.header["CRVAL1"], cube.header["CRVAL2"])
    c = SkyCoord(coordinate, unit=(u.deg, u.deg))
    logging.info(c)

    MRO = await loop.run_in_executor(None, partial(
        EarthLocation.of_site,
        'mro'
    ))
    # keck = EarthLocation.from_geodetic(lat=19.8283*u.deg, lon=-155.4783*u.deg, height=4160*u.m)
    barycorr = c.radial_velocity_correction(obstime=Time("2021-11-14"), location=MRO)

    restfreq = 1.420405752 * u.GHz  # rest frequency of HI
    freq_to_vel = u.doppler_optical(restfreq)  # using the radio convention
    vel_askap = (cube.spectral_axis).to(
        u.km / u.s, equivalencies=freq_to_vel
    ) - barycorr / 2

    # serach NVSS or SUMSS for continuum sources in the field

    if cube.header["CRVAL2"] > -40:
        result = await loop.run_in_executor(None, partial(
            Vizier(column_filters={"S1.4": ">200"}, row_limit=-1).query_constraints,
            catalog="VIII/65/nvss",
            RAJ2000=">{} & <{}".format(c.ra.deg - 2.5, c.ra.deg + 2.5),
            DEJ2000=">{} & <{}".format(c.dec.deg - 2.5, c.dec.deg + 2.5),
        ))
        logging.info(f"Dec = {cube.header['CRVAL2']}")
        logging.info("Dec > -40, searching NVSS for continuum sources in the field.")
    else:
        result = await loop.run_in_executor(None, partial(
            Vizier.query_constrants,
            catalog="VIII/81B/sumss212",
            RAJ2000=">{} & <{}".format(c.ra.deg - 2.5, c.ra.deg + 2.5),
            DEJ2000=">{} & <{}".format(c.dec.deg - 2.5, c.dec.deg + 2.5),
            dMajAxis="<45",
            St=">150",
        ))
        logging.info(f"Dec = {cube.header['CRVAL2']}")
        logging.info("Dec < -40, searching SUMSS for continuum sources in the field.")
    logging.info(f"number of continuum sources found in the field: {len(result[0])}")

    for i in range(len(result[0])):
        logging.info(f'{i+1}/{len(result[0])}')
        coord = "{} {}".format(
            result[0]["RAJ2000"][i].replace(" ", ":"),
            result[0]["DEJ2000"][i].replace(" ", ":"),
        )
        c2 = SkyCoord(coord, unit=(u.hourangle, u.deg))
        pixels_askap = c2.to_pixel(WCS(cube.header))
        logging.info(coord)
        logging.info(pixels_askap)

        spectrum_askap = cube[
            :, int(pixels_askap[1]), int(pixels_askap[0])
        ]  # 10:09:10 -28:55:57
        # tau_askap = np.log(spectrum_askap.value + 1) * -1.0
        rms = np.sqrt(np.mean(spectrum_askap.value**2))

        # plot
        fig = plt.figure(figsize=(16, 12))
        ax = fig.add_subplot(111)
        ax.set_title(
            "{}{}".format(
                result[0]["RAJ2000"][i].replace(" ", ":"),
                result[0]["DEJ2000"][i].replace(" ", ":"),
            ),
            fontsize=20,
        )

        plt.plot(vel_askap, spectrum_askap.value, "C0", linewidth=3, label="ASKAP")
        ax.axhspan(0 - 3 * rms, 3 * rms, alpha=0.5, color="lightgrey")
        # plt.title('102809-264418', fontsize=30)
        plt.ylabel("I", fontsize=28)
        plt.xlabel("v [km/s]", fontsize=28)
        # plt.xlim(-100,100)
        # plt.ylim(0.92,1.02)
        plt.axhline(0, color="k", linestyle="--")
        plt.legend(fontsize=20)
        ax.tick_params(axis="both", which="major", labelsize=25)
        filename = os.path.join(
            output_dir,
            f'{result[0]["RAJ2000"][i].replace(" ", "")}{result[0]["DEJ2000"][i].replace(" ", "")}_ASKAP_spectra.png'
        )
        await loop.run_in_executor(None, partial(
            fig.savefig,
            filename
        ))
    end = time.time()
    logging.info(f'Extract spectra duration {end-start} s')


async def main(argv):
    start = time.time()
    loop = asyncio.get_running_loop()
    args = parse_args(argv)

    # setup output directories
    if not os.path.exists(args.output):
        logging.info(f"Creating output directory {args.output}")
        os.mkdir(args.output)
    output_dir = os.path.join(args.output, args.name)
    if not os.path.exists(output_dir):
        logging.info(f"Creating output subdirectory {output_dir}")
        os.mkdir(output_dir)
    filename = os.path.splitext(os.path.basename(args.input))[0]

    # read cube
    cube = await loop.run_in_executor(None, partial(SpectralCube.read, args.input))
    await asyncio.gather(
        make_moment_map(filename, cube, output_dir),
        calculate_rms(args.input, args.name, cube, output_dir),
        calculate_peak_intensity(cube, filename, args.name, output_dir),
        extract_spectra(cube, output_dir)
    )

    end = time.time()
    logging.info(f"Main execution time {end-start} s")


if __name__ == "__main__":
    argv = sys.argv[1:]
    asyncio.run(main(argv))
