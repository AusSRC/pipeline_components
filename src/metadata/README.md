## Metadata

Get metadata from evaluation files into the database or as part of the pipelines. Generally two steps:

1. Download evaluation files (`download_evaluation_files.py`)
2. Extract metadata (either `get_footprint_files.py` or `get_slurm_output.py`)

## Usage examples

### Download evaluation files

```
python download_evaluation_files.py -s 40905 -p AS102 -o ./wallaby
```

### Get footprint files (POSSUM)

```
python get_footprint_files.py -f ./possum
```

### Get slurm output (WALLABY)

```
python get_slurm_output.py -s 40905 -f wallaby -d sofiax.ini
```
