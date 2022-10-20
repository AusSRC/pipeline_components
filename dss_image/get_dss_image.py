#!/usr/bin/env python3

import io
import os
import sys
import math
import asyncio
import asyncpg
import argparse
import logging
from dotenv import load_dotenv

import numpy as np
import matplotlib.pyplot as plt
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astroquery.skyview import SkyView


logging.basicConfig(level=logging.INFO)


def optical_overlay(mom0):
    with io.BytesIO() as buf:
        buf.write(mom0)
        buf.seek(0)
        hdu = fits.open(buf)[0]
        mom0 = hdu.data
        header = hdu.header

    wcs = WCS(header)
    nx = header["NAXIS1"]
    ny = header["NAXIS2"]
    lon, lat = wcs.all_pix2world(nx / 2, ny / 2, 0)
    tmp1, tmp3 = wcs.all_pix2world(0, ny / 2, 0)
    tmp2, tmp4 = wcs.all_pix2world(nx, ny / 2, 0)
    width = np.rad2deg(
        math.acos(
            math.sin(np.deg2rad(tmp3)) * math.sin(np.deg2rad(tmp4)) +
            math.cos(np.deg2rad(tmp3)) * math.cos(np.deg2rad(tmp4)) * math.cos(np.deg2rad(tmp1 - tmp2))
        )
    )
    tmp1, tmp3 = wcs.all_pix2world(nx / 2, 0, 0)
    tmp2, tmp4 = wcs.all_pix2world(nx / 2, ny, 0)
    height = np.rad2deg(
        math.acos(
            math.sin(np.deg2rad(tmp3)) * math.sin(np.deg2rad(tmp4)) +
            math.cos(np.deg2rad(tmp3)) * math.cos(np.deg2rad(tmp4)) * math.cos(np.deg2rad(tmp1 - tmp2))
        )
    )

    # fetch DSS image
    hdulist = SkyView.get_images(
        position=f"{lon * u.degree} {lat * u.degree}",
        survey=["DSS"],
        coordinates="J2000",
        projection="Tan",
        width=width*u.deg,
        height=height*u.deg,
        cache=None
    )
    hdu_opt = hdulist[0][0]
    wcs_opt = WCS(hdu_opt.header)

    fig = plt.figure()
    ax = plt.subplot(1, 1, 1, projection=wcs_opt)
    ax.imshow(hdu_opt.data, origin="lower")
    ax.contour(
        mom0,
        transform=ax.get_transform(wcs),
        levels=np.logspace(2.0, 5.0, 10),
        colors="lightgrey",
        alpha=1.0
    )
    ax.grid(color="grey", ls="solid")
    ax.set_xlabel("Right ascension (J2000)")
    ax.set_ylabel("Declination (J2000)")
    ax.tick_params(axis="x", which="both", left=False, right=False)
    ax.tick_params(axis="y", which="both", top=False, bottom=False)
    ax.set_title("DSS + Moment 0")
    ax.set_aspect(np.abs(wcs_opt.wcs.cdelt[1] / wcs_opt.wcs.cdelt[0]))
    plt.tight_layout()

    return plt


async def add_optical_counterpart(conn, product_id, mom0, dry_run=False):
    """Update product with optical DSS image

    """
    # Get optical DSS image
    try:
        plt = optical_overlay(mom0)
        with io.BytesIO() as buf:
            plt.savefig(buf, format='png')
            buf.seek(0)
            optical = buf.read()
            plt.close()
            if not dry_run:
                await conn.execute(
                    'UPDATE wallaby.product SET plot=$1 WHERE id=$2',
                    optical,
                    product_id
                )
                logging.info(f'Updated product id: {product_id} added DSS image')
    except Exception as e:
        logging.warning(f'Unable to save optical overlay plot with error: {e}')


async def main(argv):
    # Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--run', type=str, required=True, help='Run name for detections')
    parser.add_argument(
        '-e', '--env', type=str, required=False,
        help='Database credentials',
        default='database.env'
    )
    parser.add_argument('-d', '--dry_run', dest='dry_run', action='store_true', help='Dry run mode', default=False)
    args = parser.parse_args(argv)
    load_dotenv(args.env)

    # Database credentials
    creds = {
        'host': os.environ['DATABASE_HOST'],
        'database': os.environ['DATABASE_NAME'],
        'user': os.environ['DATABASE_USER'],
        'password': os.environ['DATABASE_PASSWORD'],
    }

    # Fetch runs and detections
    conn = await asyncpg.connect(**creds)
    run = await conn.fetchrow(
        'SELECT * FROM wallaby.run WHERE name=$1',
        args.run
    )
    if run is None:
        raise Exception(f"Run with name {args.run} could not be found") 
    logging.info(f"Adding DSS images to detection products in run {args.run}")
    detections = await conn.fetch(
        'SELECT * FROM wallaby.detection WHERE run_id=$1',
        int(run['id'])
    )
    logging.info(f'Updating {len(detections)} detection products')

    # Iterate over detections
    for i, d in enumerate(detections):
        logging.info(f'{i}/{len(detections)}')
        product = await conn.fetchrow(
            'SELECT * FROM wallaby.product WHERE detection_id=$1',
            int(d['id'])
        )
        if product['plot'] is None:
            await add_optical_counterpart(conn, int(product['id']), product['mom0'], args.dry_run)
        else:
            logging.info('Existing optical image - skipping')

    # Close
    await conn.close()


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
