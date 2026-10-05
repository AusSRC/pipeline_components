#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// ----------------------------------------------------------------------------------------
// Database
//
// Generic processes for interacting with a survey database (WALLABY and DINGO). These wrap
// aussrc_pipeline_components.database.
//
// Required params:
//      AUSSRC_TOOLS_IMAGE      Container image with aussrc_pipeline_components installed
//      DATABASE_ENV            Database credentials file with DATABASE_HOST, DATABASE_NAME,
//                              DATABASE_USER, DATABASE_PASSWORD, DATABASE_PORT and
//                              DATABASE_SCHEMA
//      SCRATCH_ROOT            Scratch filesystem to bind into the container
// ----------------------------------------------------------------------------------------

// Create an entry in the run table for a run name. Does nothing if the run already exists,
// so it is safe to use before or after SoFiAX has written to the same run.
//
//      create_run(moment0.out.done, run_name)
process create_run {
    container = params.AUSSRC_TOOLS_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val ready
        val run_name

    output:
        val run_name, emit: run_name

    script:
        """
        #!/bin/bash

        python3 -u -m aussrc_pipeline_components.database.create_run \
            -r $run_name \
            -e ${params.DATABASE_ENV}
        """
}
