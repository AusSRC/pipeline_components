#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// ----------------------------------------------------------------------------------------
// Processes
// ----------------------------------------------------------------------------------------

process mosaic {
    container = params.AUSSRC_TOOLS_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val ready
        val output_directory
        val output_file

    output:
        val output_file, emit: output_mom_file

    script:
        """
        #!/bin/bash
        python3 -u -m aussrc_pipeline_components.mom0.run_wallmerge \
            $output_directory \
            $output_file
        """
}

process compress {
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val ready
        val output_file

    output:
	    val true, emit: ready

    script:
        """
        #!/bin/bash

        gzip -f $output_file
        """
}

process plot_frequency_distribution {
    container = params.AUSSRC_TOOLS_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val ready
        val run_name
        val output_directory
        val output_file

    output:
        val true, emit: ready

    script:
        """
        #!/bin/bash

        python3 -m aussrc_pipeline_components.plots.plot_frequency_distribution_xml \
            -r $run_name -i $output_directory -o $output_file
        """
}

// Add a file to the run in the database. Not used by the workflows in this module.
process database_insert {
    container = params.AUSSRC_TOOLS_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val ready
        val column
        val run_name
        val database_env
        val file

    output:
	    val true, emit: ready

    script:
        """
        #!/bin/bash

        python3 -m aussrc_pipeline_components.plots.add_plot_to_database \
            -c $column -r $run_name -e $database_env -f $file
        """
}

process cleanup {
    executor = 'local'

    input:
        val mom0_ready
        val diagnostic_plot_ready
        val output_directory
        val prefix

    output:
        val true, emit: ready

    script:
        """
        #!/bin/bash
        rm -rf $output_directory/$prefix*
        """
}

// ----------------------------------------------------------------------------------------
// Workflow
// ----------------------------------------------------------------------------------------

// Merge the moment 0 maps in the output directory into a single (compressed) file
workflow moment0 {
    take:
        ready
        output_directory
        output_file

    main:
        mosaic(ready,
               output_directory,
               output_file)
        compress(mosaic.out.output_mom_file, mosaic.out.output_mom_file)

    emit:
        done = compress.out.ready
}

// Plot the frequency distribution of the detections in the output directory
workflow diagnostic_plot {
    take:
        ready
        run_name
        output_directory
        output_file

    main:
        plot_frequency_distribution(ready, run_name, output_directory, output_file)

    emit:
        done = plot_frequency_distribution.out.ready
}

// ----------------------------------------------------------------------------------------
