import os
import numpy as np
import argparse
import hashlib
import logging

from astropy.io import fits

# Set up the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create a formatter and add it to the console handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the console handler to the logger
logger.addHandler(console_handler)


def get_fits_header_bytes(infile):
    with fits.open(infile) as hdulist:
        header = hdulist[0].header

    # get header as string and count bytes
    header_str = str(header)
    header_bytes = header_str.encode('utf-8')
    num_bytes = len(header_bytes)

    return num_bytes, header_bytes


def get_fits_image_size_and_num_freq(infile, chan_axis):
    with fits.open(infile) as hdu:
        header = hdu[0].header

    pixel_size = int(header['BITPIX'])
    if pixel_size == 8:
        pixel_size = 1
    elif pixel_size == 16:
        pixel_size = 2
    elif pixel_size == -32 or pixel_size == 32:
        pixel_size = 4
    elif pixel_size == -64:
        pixel_size = 8
    else:
        raise ValueError('Unknown BITPIX')

    image_size = int(header['NAXIS1']) * int(header['NAXIS2']) * pixel_size
    num_freq = int(header[chan_axis])

    return image_size, num_freq


def md5_channels(infile, lower, upper, chan_axis):
    if lower < 0:
        raise ValueError("lower < 0")

    if upper < lower:
        raise ValueError("upper < lower")

    header_size, _ = get_fits_header_bytes(infile)
    image_size, num_chan = get_fits_image_size_and_num_freq(infile, chan_axis)

    if upper >= num_chan:
        raise ValueError("upper >= number of channels")

    hash_obj = hashlib.sha256()

    logger.info(f"Opening {infile}, header size {header_size}, image size {image_size}")
    count = 0

    with open(infile, 'rb') as in_obj:
        in_obj.seek(header_size + (lower * image_size))
        for i in range(lower, upper+1):
            count += 1
            data = in_obj.read(image_size)
            if not data:
                raise Exception('Unable to read bytes')
            hash_obj.update(data)

            logger.info(f"Reading channel {i} of {upper} count {count}")

    return hash_obj


def main(args):
    hash_obj = md5_channels(args.input, args.lower, args.upper, args.axis)
    logger.info(f"Digest: {hash_obj.hexdigest()}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MD5 fits')
    parser.add_argument('--input', help='Input file path', required=True)
    parser.add_argument('--lower', help='Lower bound channel', required=True, type=int)
    parser.add_argument('--upper', help='Upper bound channel', required=True, type=int)
    parser.add_argument('--axis', help='Channel axis', required=True, default='NAXIS4')
    args = parser.parse_args()
    main(args)
