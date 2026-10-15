#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// ----------------------------------------------------------------------------------------
// Processes
// ----------------------------------------------------------------------------------------

process download_singularity {
    executor = 'local'
    debug true

    input:
        val images

    output:
        val true, emit: ready

    shell:
        // Image filenames match the nextflow singularity cache naming convention
        pull_commands = images.collect { image ->
            def name = image.replaceAll('^docker://', '')
            def img = "${params.SINGULARITY_CACHEDIR}/${name.replaceAll('[/:]', '-')}.img"
            "[ -f ${img} ] || singularity pull ${img} docker://${name}"
        }.join('\n        ')

        '''
        #!/bin/bash

        lock_acquire() {
            # Open a file descriptor to lock file
            exec {LOCKFD}>!{params.SINGULARITY_CACHEDIR}/container.lock || return 1

            # Block until an exclusive lock can be obtained on the file descriptor
            flock -x $LOCKFD
        }

        lock_release() {
            test "$LOCKFD" || return 1

            # Close lock file descriptor, thereby releasing exclusive lock
            exec {LOCKFD}>&- && unset LOCKFD
        }

        lock_acquire || { echo >&2 "Error: failed to acquire lock"; exit 1; }

        !{pull_commands}

        lock_release
        '''
}

// ----------------------------------------------------------------------------------------
// Workflow
// ----------------------------------------------------------------------------------------

workflow download_containers {
    take:
        images

    main:
        download_singularity(images)

    emit:
        ready = download_singularity.out.ready
}
