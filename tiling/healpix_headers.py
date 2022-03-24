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
        '-o', '--output_directory', type=str, help='Output directory for .hdr files', required=False
    )
    args = parser.parse_args(argv)
    return args


def create_healpix_fits_headers(ra, dec, filename):
    """Function for creating FITS header files for reprojected POSSUM cubes
    
    """
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
    hdu.header.set('CTYPE1', 'RA---HPX', 'Longitude in a HPX projection')
    hdu.header.set('CTYPE2', 'DEC--HPX', 'Latitude in a HPX projection')
    hdu.header.set('CRVAL1', ra, '[deg]')
    hdu.header.set('CRVAL2', dec, '[deg]')
    hdu.header.set('PV2_1', 4, 'HPX H parameter (longitude)')
    hdu.header.set('PV2_2', 3, 'HPX K parameter (latitude)')
    del hdu.header['EXTEND']
    
    # Write to .hdr file
    lines = hdu.header.tostring(sep='\n').strip().split('\n')
    with open(filename, 'w') as f:
        f.writelines(f'{line}\n' for line in lines)
    
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
            pixel = hp.ang2pix(args.NSIDE, ra, dec, nest=False, lonlat=True)
            RA, DEC = hp.pix2ang(nside=args.NSIDE, ipix=pixel, nest=False, lonlat=True)
            filename = f"{args.output_directory}/{round(RA, 2)}_{round(DEC, 2)}.hdr"
            create_healpix_fits_headers(RA, DEC, filename)


if __name__ == '__main__':
    main(sys.argv[1:])
