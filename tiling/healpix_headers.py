#!/usr/bin/env python3

import os
import sys
import argparse
import healpy as hp
from astropy.io import fits


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--NSIDE', type=int, required=False, default=32)
    parser.add_argument('-i', '--input', type=str, help='Input image cube', required=True)
    parser.add_argument(
        '-o', '--output', type=str, help='Output directory for .hdr files', required=False
    )
    args = parser.parse_args(argv)
    return args


def create_healpix_fits_headers(ra, dec, filename):
    """Write .hdr fits headers for a Healpix reprojected image cube.

    """
    # TODO(austin): what are these constants and do they always apply to the POSSUM cubes?
    # Set header
    hdu = fits.PrimaryHDU()
    hdu.header.set('BITPIX', -32)
    hdu.header.set('NAXIS', 2)
    hdu.header.set('NAXIS1', 2048)
    hdu.header.set('NAXIS2', 2048)
    hdu.header.set('CRPIX1', 1024.5, 'Coordinate reference pixel')
    hdu.header.set('CRPIX2', 1024.5, 'Coordinate reference pixel')
    hdu.header.set('CD1_1', -6.8664550781250E-04)
    hdu.header.set('CD1_2', -6.8664550781250E-04)
    hdu.header.set('CD2_1', -6.8664550781250E-04)
    hdu.header.set('CD2_2', -6.8664550781250E-04)
    hdu.header.set('CTYPE1', 'RA--HPX', 'Longitude in a HPX projection')
    hdu.header.set('CTYPE2', 'DEC--HPX', 'Latitude in a HPX projection')
    hdu.header.set('CRVAL1', ra, '[deg]')
    hdu.header.set('CRVAL2', dec, '[deg]')
    hdu.header.set('PV2_1', 4, 'HPX H parameter (longitude)')
    hdu.header.set('PV2_2', 3, 'HPX K parameter (latitude)')
    del hdu.header['EXTEND']

    # Write to .hdr file (override default)
    if os.path.exists(filename):
        os.remove(filename)
    hdul = fits.HDUList([hdu])
    hdul.writeto(filename)

    return


def main(argv):
    """Generates .hdr files for an image cube with Healpix reprojection

    Usage:
    ./healpix_headers.py -n <NSIDE> -i <image_cube> -o <output_directory>
    """
    args = parse_args(argv)

    # get arguments
    with fits.open(args.input) as hdul:
        hdr = hdul[0].header
        lon = hdr['CRVAL1']
        lat = hdr['CRVAL2']
        angular_size = hp.nside2resol(args.NSIDE, arcmin=True) / 60.0

    # grid of fits headers to write
    ra_array = [
        lon - (2 * angular_size),
        lon - angular_size,
        lon,
        lon + angular_size,
        lon + (2 * angular_size)
    ]
    dec_array = [
        lat - (2 * angular_size),
        lat - angular_size,
        lat,
        lat + angular_size,
        lat + (2 * angular_size)
    ]
    for ra in ra_array:
        for dec in dec_array:
            filename = f"{args.output}/{round(ra, 2)}_{round(dec, 2)}.hdr"
            pixel = hp.ang2pix(args.NSIDE, ra, dec, nest=False, lonlat=True)
            RA, DEC = hp.pix2ang(nside=args.NSIDE, ipix=pixel, nest=False, lonlat=True)
            create_healpix_fits_headers(RA, DEC, filename)


if __name__ == '__main__':
    main(sys.argv[1:])
