#!/usr/bin/env python3

"""
Plot summary figure for milky way detections (WALLABY)
"""

import io
import os
import sys
import math
import asyncio
import asyncpg
import argparse
import warnings
import logging
from dotenv import load_dotenv
from functools import partial
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.visualization import PercentileInterval
from astroquery.skyview import SkyView
import matplotlib.pyplot as plt


warnings.filterwarnings("ignore")
logger = logging.getLogger()
logger.setLevel(logging.INFO)
streamhdlr = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
streamhdlr.setFormatter(formatter)
logger.addHandler(streamhdlr)


C = 2.99792E8  # m/s
HI_RESTFREQ = 1.42040575e+9  # Hz


def get_aspect(ax):
    fw, fh = ax.get_figure().get_size_inches()
    _, _, w, h = ax.get_position().bounds
    disp_ratio = round((fh * h) / (fw * w), 2)
    return disp_ratio


async def milkyway_summary(pool, points, detection):
    loop = asyncio.get_running_loop()

    # Get product
    async with pool.acquire() as conn:
        product = await conn.fetchrow(
            "SELECT * FROM product WHERE detection_id=$1",
            int(detection["id"]))

    if not product:
        logger.info("No products")
        return

    if product["mom0"] is None or product["mom1"] is None or product["spec"] is None:
        logger.error(f"mom0, mom1 or spec missing for detection {detection['id']}")
        return

    if not product["pv"]:
        logger.error(f"pv missing for detection {detection['id']} [need to re-run sofia with outputs.writePV=true]")
        return

    product_id = int(product['id'])

    logger.info(f"Processing product id: {product_id}")

    # Plot figure size
    plt.rcParams["font.family"] = ["serif"]
    plt.rcParams["figure.figsize"] = (8, 8)

    # Open moment 0 image
    with io.BytesIO() as buf:
        buf.write(product["mom0"])
        buf.seek(0)
        hdu_mom0 = await loop.run_in_executor(None, partial(fits.open, buf))
        hdu_mom0 = hdu_mom0[0]
        wcs = WCS(hdu_mom0.header)
        mom0 = hdu_mom0.data

    # Open moment 1 image
    with io.BytesIO() as buf:
        buf.write(product["mom1"])
        buf.seek(0)
        hdu_mom1 = await loop.run_in_executor(None, partial(fits.open, buf))
        hdu_mom1 = hdu_mom1[0]
        mom1 = hdu_mom1.data

    # Spectrum
    with io.BytesIO() as buf:
        buf.write(product["spec"])
        buf.seek(0)
        spectrum = await loop.run_in_executor(None, partial(np.loadtxt, buf, dtype="float", comments="#", unpack=True))

    # Extract coordinate information
    nx = hdu_mom0.header["NAXIS1"]
    ny = hdu_mom0.header["NAXIS2"]
    clon, clat = wcs.all_pix2world(nx / 2, ny / 2, 0)
    tmp1, tmp3 = wcs.all_pix2world(0, ny / 2, 0)
    tmp2, tmp4 = wcs.all_pix2world(nx, ny / 2, 0)
    width = np.rad2deg(math.acos(math.sin(np.deg2rad(tmp3)) * math.sin(np.deg2rad(tmp4))
                        + math.cos(np.deg2rad(tmp3))
                        * math.cos(np.deg2rad(tmp4))
                        * math.cos(np.deg2rad(tmp1 - tmp2))))

    tmp1, tmp3 = wcs.all_pix2world(nx / 2, 0, 0)
    tmp2, tmp4 = wcs.all_pix2world(nx / 2, ny, 0)
    height = np.rad2deg(math.acos(math.sin(np.deg2rad(tmp3)) * math.sin(np.deg2rad(tmp4))
                        + math.cos(np.deg2rad(tmp3))
                        * math.cos(np.deg2rad(tmp4))
                        * math.cos(np.deg2rad(tmp1 - tmp2))))

    # Download DSS image from SkyView
    try:
        hdu_opt = await loop.run_in_executor(
            None,
            partial(
                SkyView.get_images,
                position="{}d {}d".format(clon, clat),
                survey="DSS",
                coordinates="J2000",
                projection="Tan",
                width=width * u.deg,
                height=height * u.deg,
                cache=None,
                show_progress=False,)
            )

        for h in hdu_opt:
            hdu = h[0]
            wcs_opt = WCS(hdu.header)
            break
    except Exception as e:
        logger.error(f'Download error of DSS image for product id: {product_id}, error: {e}')
        raise e

    # Plot moment 0
    ax2 = plt.subplot2grid((3, 2), (0, 0), projection=wcs)
    ax2.imshow(mom0, origin="lower")
    ax2.grid(color="grey", ls="solid")
    ax2.set_xlabel("Right ascension (J2000)")
    ax2.set_ylabel("Declination (J2000)")
    ax2.tick_params(axis="x", which="both", left=False, right=False)
    ax2.tick_params(axis="y", which="both", top=False, bottom=False)
    ax2.set_title("moment 0")
    ar = get_aspect(ax2)

    # Plot DSS image with HI contours
    interval = PercentileInterval(99.0)
    bmin, bmax = interval.get_limits(hdu.data)
    ax = plt.subplot2grid((3, 2), (0, 1), projection=wcs_opt)
    ax.imshow(hdu.data, origin="lower", vmin=bmin, vmax=bmax, aspect=str(ar))
    ax.contour(
        hdu_mom0.data,
        transform=ax.get_transform(wcs),
        levels=np.logspace(2.0, 5.0, 10),
        colors="lightgrey",
        alpha=1.0,
    )
    ax.grid(color="grey", ls="solid")
    ax.set_xlabel("Right ascension (J2000)")
    ax.set_ylabel("Declination (J2000)")
    ax.tick_params(axis="x", which="both", left=False, right=False)
    ax.tick_params(axis="y", which="both", top=False, bottom=False)
    ax.set_title("DSS + moment 0")

    # Plot moment 1
    interval = PercentileInterval(95.0)
    bmin, bmax = interval.get_limits(mom1)
    ax3 = plt.subplot2grid((3, 2), (1, 0), projection=wcs)
    ax3.imshow(
        hdu_mom1.data,
        origin="lower",
        vmin=bmin,
        vmax=bmax,
        cmap=plt.get_cmap("gist_rainbow"),)

    ax3.grid(color="grey", ls="solid")
    ax3.set_xlabel("Right ascension (J2000)")
    ax3.set_ylabel("Declination (J2000)")
    ax3.tick_params(axis="x", which="both", left=False, right=False)
    ax3.tick_params(axis="y", which="both", top=False, bottom=False)
    ax3.set_title("moment 1")

    # Plot spectrum
    velocity = C * (HI_RESTFREQ / spectrum[1] - 1)
    xaxis = velocity / 1e3  # km/s
    data = 1000.0 * np.nan_to_num(spectrum[2])
    xmin = np.nanmin(xaxis)
    xmax = np.nanmax(xaxis)
    ymin = np.nanmin(data)
    ymax = np.nanmax(data)
    ymin -= 0.1 * (ymax - ymin)
    ymax += 0.1 * (ymax - ymin)
    ax4 = plt.subplot2grid((3, 2), (1, 1))
    ax4.step(xaxis, data, where="mid", color="royalblue")
    ax4.set_xlabel("Velocity (km/s)")
    ax4.set_ylabel("Flux density (mJy)")
    ax4.set_title("spectrum")
    ax4.grid(True)
    ax4.set_xlim([xmin, xmax])
    ax4.set_ylim([ymin, ymax])
    ax4.set_aspect('auto')

    # Plot location of detection
    ax5 = plt.subplot2grid((3, 2), (2, 0), colspan=2)
    ax5.scatter(points[0], points[1], marker='.', alpha=0.5)
    ax5.scatter(detection['x'], detection['y'], marker='o', alpha=0.5, color='red')
    ax5.set_title("Detection location")
    ax5.set_aspect('auto')

    plt.suptitle(detection["name"].replace("_", " ").replace("-", "−"), fontsize=16)
    plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0.5, hspace=0.6)

    with io.BytesIO() as buf:
        plt.savefig(buf, format="png")
        buf.seek(0)
        summary_plot = buf.read()
        plt.close()

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE product SET plot=$1 WHERE id=$2",
            summary_plot,
            product_id
        )
    logger.info(f"Updated product id: {product_id}")
    return


async def main(argv):
    """Download summary plots for Milkyway detections from SoFiA for the SoFiAX_services portal.

    Usage:
    python3 milkyway_summary.py -r <RUN_NAME> -e <DATABASE_ENV>

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--run', type=str, required=True, help='Run name')
    parser.add_argument('-e', '--env', type=str, required=False, default='database.env', help='Database environment file')
    args = parser.parse_args(argv)
    assert os.path.exists(args.env), f'Provided environment file {args.env} does not exist'
    load_dotenv(args.env)
    db_creds = {
        "host": os.environ['DATABASE_HOST'],
        "database": os.environ['DATABASE_NAME'],
        "user": os.environ['DATABASE_USER'],
        "password": os.environ['DATABASE_PASSWORD']
    }
    pool = await asyncpg.create_pool(
        **db_creds,
        server_settings={'search_path': os.environ['DATABASE_SCHEMA']}
    )

    # Extract detections from run
    logger.info(f'Generating milkyway summary figures for run {args.run}')
    async with pool.acquire() as conn:
        run = await conn.fetchrow('SELECT * FROM run WHERE name=$1', args.run)
        if run is None:
            raise Exception(f'No run with name {args.run} exists.')
        detections = await conn.fetch('SELECT * FROM detection WHERE run_id=$1 ORDER BY id ASC', int(run['id']))
        logger.info(f'Updating {len(detections)} product entries')

    # scatter plot of detection positions
    x = [int(d['x']) for d in detections]
    y = [int(d['y']) for d in detections]
    points = np.array([x, y])

    # Update
    await milkyway_summary(pool, points, detections[0])

    # Finish
    await pool.close()


if __name__ == "__main__":
    argv = sys.argv[1:]
    asyncio.run(main(argv))
