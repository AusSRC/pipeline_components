#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// ----------------------------------------------------------------------------------------
// Mosaicking
//
// Generic processes for mosaicking image cubes with linmos (ASKAPsoft). Each mosaic is
// described by a single "job" map, constructed by the pipeline
//
//      [
//          name:        "TILE_288-38",                 Label for the mosaic
//          images:      [image cube, ...],             Input image cubes
//          weights:     [weights cube, ...],           Input weights cubes
//          image_out:   "/path/to/TILE_288-38_image",  Output image cube
//          weights_out: "/path/to/TILE_288-38_weights" Output weights cube ("" for none)
//          config:      "/path/to/linmos.conf",        linmos configuration file to write
//          history:     ["...", ...]                   Lines for the output image history
//      ]
//
// File names can be given with or without the .fits extension. A mosaic is not run again
// if the output image cube already exists.
//
// Required params:
//      AUSSRC_PIPELINE_COMPONENTS_IMAGE    Container image with aussrc_pipeline_components
//      ASKAPSOFT_IMAGE                     Container image for ASKAPsoft (linmos)
//      SINGULARITY_CACHEDIR                Directory with the singularity images
//      SCRATCH_ROOT                        Scratch filesystem to bind into the container
//
// The resources for linmos (nodes, tasks and cpus per task) are set by the pipeline with
// clusterOptions for the linmos and linmos_mpi processes. The linmos log is written to the
// standard output of the process (.command.out).
// ----------------------------------------------------------------------------------------

templates = "${moduleDir}/../templates"

// Path to the ASKAPsoft image in the singularity cache (nextflow naming convention)
def askapsoft_image() {
    def name = params.ASKAPSOFT_IMAGE.replaceAll('^docker://', '').replaceAll('[/:]', '-')
    return "${params.SINGULARITY_CACHEDIR}/${name}.img"
}

// Output files [image cube, weights cube] of a job
def mosaic_files(job) {
    def files = [job.image_out, job.weights_out].findAll { it }
    return files.collect { it.toString().replaceAll(/\.fits$/, '') + '.fits' }
}

// ----------------------------------------------------------------------------------------
// Processes
// ----------------------------------------------------------------------------------------

// Write the linmos configuration file for a job from the template
import groovy.json.JsonOutput
process linmos_config {
    container = params.AUSSRC_PIPELINE_COMPONENTS_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val job

    output:
        val job, emit: job

    script:
        job_json = JsonOutput.toJson(job)
        """
        #!python3

        import os
        import json
        from jinja2 import Environment, FileSystemLoader

        job = json.loads(r'''${job_json}''')

        def strip(filename):
            return filename[:-len('.fits')] if filename.endswith('.fits') else filename

        j2_env = Environment(loader=FileSystemLoader('${templates}'), trim_blocks=True)
        result = j2_env.get_template('linmos.j2').render(
            images=[strip(f) for f in job['images']],
            weights=[strip(f) for f in job['weights']],
            image_out=strip(job['image_out']),
            weight_out=strip(job.get('weights_out') or ''),
            image_history=job.get('history') or [],
        )

        for path in [job['config'], job['image_out']]:
            os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(job['config'], 'w') as f:
            print(result, file=f)
        """
}

// Run linmos for a job with MPI
process linmos_mpi {
    input:
        val job

    output:
        val mosaic, emit: mosaic
        val job, emit: job

    script:
        mosaic = mosaic_files(job)
        """
        #!/bin/bash

        if ! test -f ${mosaic[0]}; then
            export OMP_NUM_THREADS=1
            srun -N \$SLURM_NNODES -n \$SLURM_NTASKS -c \$SLURM_CPUS_PER_TASK \
                singularity exec --bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT} \
                ${askapsoft_image()} \
                linmos-mpi -c ${job.config} -l ${templates}/linmos.log_cfg
        fi
        """
}

// Run linmos for a job without MPI
process linmos {
    input:
        val job

    output:
        val mosaic, emit: mosaic
        val job, emit: job

    script:
        mosaic = mosaic_files(job)
        """
        #!/bin/bash

        if ! test -f ${mosaic[0]}; then
            export OMP_NUM_THREADS=1
            singularity exec --bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT} \
                ${askapsoft_image()} \
                linmos -c ${job.config} -l ${templates}/linmos.log_cfg
        fi
        """
}

// ----------------------------------------------------------------------------------------
// Workflows
// ----------------------------------------------------------------------------------------

// Mosaic the image cubes of each job with linmos (MPI). Emits the output files of each job
// as [image cube, weights cube]
workflow mosaic {
    take:
        job

    main:
        linmos_config(job)
        linmos_mpi(linmos_config.out.job)

    emit:
        mosaic = linmos_mpi.out.mosaic
        job = linmos_mpi.out.job
}
