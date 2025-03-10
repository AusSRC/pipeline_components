import os
import numpy as np
import argparse
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


def split_number(num, n):
    if n <= 0:
        raise ValueError("n must not be <= 0")

    # Calculate the size of each part
    size = num // n

    # Calculate the remainder
    remainder = num % n

    # Create the parts
    parts = []
    lower_bound = 0
    for i in range(n):
        # Calculate the upper bound
        if i < remainder:
            upper_bound = lower_bound + size
        else:
            upper_bound = lower_bound + size - 1

        # Add the range to the parts list
        parts.append((lower_bound, upper_bound))

        # Update the lower bound
        lower_bound = upper_bound + 1

    return parts


def get_fits_header_bytes(infile):
    with fits.open(infile) as hdulist:
        header = hdulist[0].header

    # get header as string and count bytes
    #header_str = str(header)
    #header_bytes = header_str.encode('utf-8')
    #num_bytes = len(header_bytes)

    return header


def get_fits_image_size_and_num_freq(infile):
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
    num_freq = int(header['NAXIS4'])

    return image_size, num_freq


def split_fits(infile, outpath, part):
    abs_outpath = os.path.abspath(outpath)

    try:
        os.makedirs(abs_outpath, exist_ok=True)
    except FileExistsError:
        pass

    lower = part[0]
    upper = part[len(part)-1]

    in_filename = os.path.basename(infile)
    out_filename = f"{abs_outpath}/split_{lower}-{upper}_{in_filename}"

    logger.info(f"Creating {out_filename}")

    header = get_fits_header_bytes(infile)
    header['NAXIS4'] = (upper-lower)+1
    header.update()

    header_str = str(header)
    header_bytes = header_str.encode('utf-8')
    header_size = len(header_bytes)

    image_size, _ = get_fits_image_size_and_num_freq(infile)

    with open(out_filename, 'wb') as obj:
        obj.write(header_bytes)

        with open(infile, 'rb') as in_obj:
            in_obj.seek(header_size + (lower * image_size))
            count = 0
            for i in range(lower, upper+1):
                count += 1
                image_bytes = in_obj.read(image_size)
                if not image_bytes:
                    raise Exception('Unable to read bytes')
                obj.write(image_bytes)
                obj.flush()

                logger.info(f"Copying channel {i} of {upper} count {count}")

    # Pad the end of the file with 0 to make sure its multiples of 2880
    filesize = os.path.getsize(out_filename)
    if filesize % 2880 != 0:
        padding_size = 2880 - (filesize % 2880)
        with open(out_filename, 'ab') as f:
            f.seek(0, os.SEEK_END)
            f.write(b'\0' * padding_size)


def main(args):
    _, num_freq = get_fits_image_size_and_num_freq(args.input)
    # your main code here
    parts = split_number(num_freq, args.splits)

    for p in parts:
        split_fits(args.input, args.output, p)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FITS cube splitter')
    parser.add_argument('--input', help='Input file path', required=True)
    parser.add_argument('--output', help='Output directory', required=True)
    parser.add_argument('--splits', type=int, help='Number of splits', required=True)
    args = parser.parse_args()
    main(args)
