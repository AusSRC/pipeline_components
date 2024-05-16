#!/usr/bin/env python3

"""
Add metadata to FITS header
"""

import os
import sys
import logging
import argparse
from astropy.io import fits


logging.basicConfig(level=logging.INFO)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", dest="image_cubes", nargs="+", help="Image cube files to add metadata to.")
    parser.add_argument("-k", dest="keys", nargs="+", help="Keys to add to FITS header table", required=False)
    parser.add_argument("-v", dest="values", nargs="+", help="Values to add to FITS header table", required=False)
    args = parser.parse_args(argv)
    logging.info(args)

    # Assert key value length are the same
    assert len(args.keys) == len(args.values), "Expect same number of keys and values to add to FITS header"
    kv_dict = {}
    for i, v in enumerate(args.values):
        key = args.keys[i]
        if key in kv_dict.keys():
            value = kv_dict[key].append(v)
        else:
            kv_dict[key] = [v]

    logging.info(kv_dict)

    # Open fits cubes
    for f in args.image_cubes:
        if not os.path.exists(f):
            raise Exception(f"Image cube file could not be found {f}")

    # Add to header
    for f in args.image_cubes:
        with fits.open(f, mode="update") as hdu:
            hdr = hdu[0].header
            for k, v_list in kv_dict.items():
                for v in v_list:
                    if k in hdr and k != 'HISTORY' and k != 'COMMENT':
                        v_upd = f'{hdr[k]} {v}'
                        hdr[k] = v_upd.replace('\n', ' ')
                        logging.info(f'[{f}] Updating header {k} = {v_upd}')
                    else:
                        hdr[k] = v
                        logging.info(f'[{f}] Added to header {k} = {v}')


if __name__ == "__main__":
    main(sys.argv[1:])
