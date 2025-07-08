# Changelog

All notable changes to the Docker image `docker://aussrc/casda_download` will be documented in this file.

## [v1.0.2]

- Added download evaluation files script
- Moved download_files (with retry + resume from existing file) to a separate folder to be used in both download codes

## [v1.0.1]

- Download from point of failure with retries for all files
- Use keyring on setonix to allow for recent versions of astroquery > 0.4.6

## [v1.0.0]

- Default queries for downloading relevant files for the following ASKAP projects: EMU, WALLABY, POSSUM and DINGO