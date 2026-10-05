# AusSRC pipeline components

Docker images and component scripts for AusSRC ASKAP science data post-processing workflows. These components provide code snippets for generic functionality used across these workflows. They are used across the following pipelines

- [POSSUM pipeline](https://github.com/AusSRC/POSSUM_workflow)
- [WALLABY pipeline](https://github.com/AusSRC/WALLABY_pipelines)
- [DINGO pipeline](https://github.com/AusSRC/DINGO_workflows)

## Container images

The Python code is installed as the `aussrc_pipeline_components` package in two images, built from this repository.

| Image | Dockerfile | Contents |
| --- | --- | --- |
| `aussrc/pipeline_components` | [Dockerfile](Dockerfile) | All components except CASA tiling |
| `aussrc/pipeline_components_casa` | [Dockerfile.casa](Dockerfile.casa) | All components, plus CASA and the HPX tiling requirements |

Scripts are run as modules from inside the container

```
python3 -m aussrc_pipeline_components.casda.download -q "<query>" -o <output_dir> -m <manifest> -c <credentials>
```

## Components

| Component | Description |
| --- | --- |
| [casda](src/casda/README.md) | Download image cubes and evaluation files from CASDA |
| [hpx_tiles](src/hpx_tiles/README.md) | HPX tiling of POSSUM data cubes using CASA |
| [metadata](src/metadata/README.md) | FITS header and observation metadata tools |
| mom0 | Merge moment 0 maps |
| mosaicking | Update linmos configuration |
| plots | Diagnostic and summary plots |
| source_finding | Update SoFiAX configuration |

## Contributing

### Structure

- `src`: Python package (`aussrc_pipeline_components`), with one subpackage per component
- `nextflow`: Nextflow modules, templates and config shared across the pipelines
- `tests`: unit tests

Requirements are listed in `pyproject.toml`. Those only needed for HPX tiling are in the `casa` optional dependencies.

### Install

```
pip install -e ".[dev]"
```

### Building images

```
docker build --platform linux/amd64 -t aussrc/pipeline_components:<tag> .
docker build --platform linux/amd64 -f Dockerfile.casa -t aussrc/pipeline_components_casa:<tag> .
docker push aussrc/pipeline_components:<tag>
docker push aussrc/pipeline_components_casa:<tag>
```
