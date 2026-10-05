#!/usr/bin/env python3

import sys
import numpy as np
from astropy.io import fits


def main():
    if len(sys.argv) != 3:
        sys.stderr.write("\n Usage: wallmerge.py cube1,cube2 <OUTPUT_FILE>\n\n")
        sys.exit(1)

    filename_cubes = sys.argv[1].split(",")
    output_file = sys.argv[2]

    try:
        hdu_cubes = [fits.open(url) for url in filename_cubes]
        hdu0_cubes = [hdu[0] for hdu in hdu_cubes]
    except Exception:
        sys.stderr.write("Failed to read data cube. Please check your input.\n")
        sys.exit(1)

    # Extract dimensions from all cubes
    axes = int(hdu0_cubes[0].header["NAXIS"])
    naxis = [
        [
            int(hdu0_cubes[cube].header["NAXIS{:d}".format(axis + 1)])
            for axis in range(axes)
        ]
        for cube in range(len(hdu0_cubes))
    ]
    naxis_out = [0 for axis in range(axes)]
    offset_out = [0 for axis in range(axes)]

    # Extract reference pixels from all cubes
    crpix = [
        [hdu0_cubes[cube].header["CRPIX{:d}".format(axis + 1)] for axis in range(axes)]
        for cube in range(len(hdu0_cubes))
    ]

    # Determine output dimensions (adapted from Miriad task 'imcomb')
    for axis in range(axes):
        minpix = int(-crpix[0][axis])
        maxpix = int(-crpix[0][axis]) + naxis[0][axis]

        for cube in range(1, len(hdu0_cubes)):
            minpix = min(minpix, int(-crpix[cube][axis]))
            maxpix = max(maxpix, int(-crpix[cube][axis]) + naxis[cube][axis])

        naxis_out[axis] = maxpix - minpix
        offset_out[axis] = -minpix

        for cube in range(len(hdu0_cubes)):
            crpix[cube][axis] -= offset_out[axis]

    print("Output cube size: " + str(naxis_out))

    # Create empty output cube
    size_out = [naxis_out[axis] for axis in range(axes)]
    cube_out = np.full(list(reversed(size_out)), 0.0, dtype=np.float32)
    hdu_data_out = fits.PrimaryHDU(data=cube_out, header=hdu0_cubes[0].header)

    # Update reference pixel
    for axis in range(axes):
        hdu_data_out.header.set("crpix{:d}".format(axis + 1), offset_out[axis])

    # Copy individual cubelets into output cube
    for cube in range(len(hdu0_cubes)):
        pix_min = [int(-crpix[cube][axis]) for axis in range(axes)]
        pix_max = [pix_min[axis] + naxis[cube][axis] for axis in range(axes)]
        print(
            "- Input cube "
            + str(cube)
            + " position: "
            + str(pix_min)
            + " - "
            + str(pix_max)
        )

        slc = tuple(
            [
                slice(pix_min[axes - axis - 1], pix_max[axes - axis - 1], 1)
                for axis in range(axes)
            ]
        )
        cube_out[slc] += hdu0_cubes[cube].data

    # Close input files again
    for cube in range(len(hdu0_cubes)):
        hdu_cubes[cube].close()

    # Write output cube
    hdu_data_out.writeto(output_file, overwrite=True)
    print(" - Output cube written")


if __name__ == "__main__":
    main()
