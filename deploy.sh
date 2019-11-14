#!/bin/sh

export SKA=/proj/sot/ska
PATH=/data/acis/ska/bin:${PATH}
cd /data/acis/ska_pkg/acis_viols_tracking

make track 2>&1 >/dev/null
make html 2>&1 >/dev/null
make deploy 2>&1 >/dev/null
