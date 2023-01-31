#!/usr/bin/env python3

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy_healpix import HEALPix
from astropy.io import fits
import sys
import argparse
import logging


logging.basicConfig(level=logging.INFO)


def parse_args(argv):

    parser = argparse.ArgumentParser()

    parser.add_argument("-i", dest="fitsimage", help="Image file", required=True)
    parser.add_argument("-pf", dest="prefix", help="Output prefix", required=True)
    parser.add_argument("-c", dest="cenfreq", help="Central frequency", required=True)
    parser.add_argument(
        "-id", dest="tileID", help="Tile ID ~ Healpix ID", required=True, type=int
    )
    parser.add_argument("-v", dest="version", help="Output version", required=True)

    args = parser.parse_args(argv)

    return args


def name(fitsimage, prefix, cenfreq, tileID, version="v1"):
    """Setting up the name to be used for tiles. The script reads
    the bmaj and stokes from the fits header. The rest of the parameters are
    flexible to change.

    fitsimage: tile image
    prefix   : prefix to use. E.g. PSM for full survey,
               PSM_pilot1 for POSSUM pilot 1
               PSM_pilot2 for POSSUM pilot 2
    cenfreq  : Central frequency (for band 1 we set it to 944MHz,
               for band 2 1296MHz)
    tileID   : tile pixel (Healpix pixel)

    version  : version of the output product. Version 1 is v1, version is v2,
               and so forth.

    """

    logging.info(f"Reading {fitsimage} header")

    hdr = fits.getheader(fitsimage)

    # get bmaj.
    bmaj = hdr["BMAJ"] * 3600.0

    # extract stokes parameter. It can be in either the 3rd or fourth axis.
    if hdr["CTYPE3"] == "STOKES":
        stokes = hdr["CRVAL3"]

    if hdr["CTYPE4"] == "STOKES":
        stokes = hdr["CRVAL4"]

    else:
        sys.exit(">>> Cannot find Stokes axis on the 3rd/4th axis")

    # stokes I=1, Q=2, U=3 and 4=V
    if int(stokes) == 1:
        stokesid = "i"

    if int(stokes) == 2:
        stokesid = "q"

    if int(stokes) == 3:
        stokesid = "u"

    if int(stokes) == 4:
        stokesid = "v"

    logging.info("Define healpix grid for nside 32")
    # define the healpix grid
    hp = HEALPix(nside=32, order="ring", frame="icrs")

    # extract the RA and DEC for a specific pixel
    center = hp.healpix_to_lonlat(tileID) * u.deg
    RA, DEC = center.value

    logging.info(f"Derived RA is {RA} degrees and DEC is {DEC} degrees")
    c = SkyCoord(ra=RA * u.degree, dec=DEC * u.degree, frame="icrs")

    h, hm, hs = c.ra.hms
    hmhs = "%s" % round(hm + (hs / 60.0))
    hmhs = hmhs.zfill(2)
    hm = "%d%s" % (h, hmhs)

    d, dm, ds = c.dec.dms
    # if dec is in the southern sky leave as is. If northen add a +.
    dmds = "%s" % round(abs(dm) + (abs(dm) / 60.0))
    dmds = dmds.zfill(2)
    if d < 0:
        dm = "%d%s" % (d, dmds)
    if d > 0:
        dm = "+%d%s" % (d, dmds)

    RADEC = "%s%s" % (hm, dm)

    outname = (
        prefix
        + "_%s" % cenfreq
        + "_%.1f" % bmaj
        + "_%s" % (RADEC)
        + "_%s" % stokesid
        + "_%s" % version
        + ".fits"
    )
    print(outname, end="")


def main(argv):
    """ Renames tile images.

    Usage:
        python renaming_tiles -i <image_name> -pf <output_prefix> -c <central_frequency>
        -id <tile_ID> -v <version number>

    Returns a new name for a tile

    """

    args = parse_args(argv)

    name(
        fitsimage=args.fitsimage,
        prefix=args.prefix,
        cenfreq=args.cenfreq,
        tileID=args.tileID,
        version=args.version,
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    main(argv)
