#!/bin/bash

BASEDIR=/projects/CIRADA/polarimetry/ASKAP/
GROUP="CIRADA-Polarimetry"

vmkdir arc:$BASEDIR/$2
vcp $1 arc:$BASEDIR/$2
vchmod g+w arc:$BASEDIR/$2 $GROUP
vchmod g+w arc:$BASEDIR/$2/$1 $GROUP
