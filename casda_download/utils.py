#!/usr/bin/env python3

import os
import sys
import time
import logging
import urllib


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'
)


def download_files(url, output, timeout=3000, check_exists=True, buffer=4*2**20, retry=3, sleep=5*60):
    """Download file from Pawsey with an URL provided by CASDA. Uses retries and restart download from
    failure if the file exists for robust download.

    Args:
        url (str):              URL from setonix
        output (str):           Output directory where the downloaded file will be written
        timeout (int):          Raise error and close connection after timeout
        check_exists (bool):    Check if file exists first before download (skip if exists)
        buffer (int):           Download size buffer
        retry (int):            Number of times to retry the download in case of failure
        sleep (int):            Duration to sleep if retrying between failure.

    """
    logging.info(f"Requesting: URL: {url} Timeout: {timeout}")
    if url is None:
        raise ValueError('URL is empty')

    if not os.path.exists(output):
        os.makedirs(output)

    downloaded_bytes = 0
    tries = 0
    while tries <= retry:
        try:
            req = urllib.request.urlopen(url, timeout=timeout)
            filename = req.info().get_filename()
            filepath = f"{output}/{filename}"
            http_size = int(req.info()['Content-Length'])

            # File exists and is same size; do nothing and return
            if check_exists and os.path.exists(filepath) and os.path.getsize(filepath) == http_size:
                logging.info(f"File exists and is expected size: {os.path.basename(filepath)} {http_size}")
                return filepath

            # Resume download from bytes already downloaded
            if os.path.exists(filepath) and os.path.getsize(filepath) != http_size:
                downloaded_bytes = os.path.getsize(filepath)
                logging.info(f"Resuming download: {os.path.basename(filepath)} {downloaded_bytes} bytes")
                headers = {'Range': f'bytes={downloaded_bytes}-'}
                mode = 'ab'

            # Starting download when there is no file
            elif not os.path.exists(filepath):
                logging.info(f"Starting download: {os.path.basename(filepath)}")
                headers = {}
                mode = 'wb'

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                with open(filepath, mode) as o:
                    while True:
                        buff = r.read(buffer)
                        if not buff:
                            break
                        o.write(buff)
                        downloaded_bytes += len(buff)

                download_size = os.path.getsize(filepath)
                if http_size != download_size:
                    raise ValueError(f"File size does not match file {download_size} and http {http_size}")

                logging.info(f"Download complete: {os.path.basename(filepath)}")
                return filepath
        except (OSError, ValueError) as e:
            tries += 1
            logging.info(f'Download error. Retry number {tries}. Error: {e}')
            logging.info(f'Sleeping for {sleep} seconds before retrying.')
            time.sleep(sleep)
    raise Exception(f'Download retried {retry} times with each failing.')
    return None
