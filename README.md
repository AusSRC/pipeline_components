# POSSUM Pipeline components

Components for the POSSUM pipeline.

### CASA

Note that we fix the version of Python CASA in the `hpx_tiles` container to ensure the tiling works with the code that we have written. There are some minor modifications (`-1` to `CRPIX1` and `CRPIX2` in header) that are required for the current version of CASA that we are using. These may break if a different version of python casa is used.

```
casatools==6.5.2.26
casatasks==6.5.2.26
```