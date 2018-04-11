#!/bin/sh

export SKA=/proj/sot/ska
PATH=/data/acis/ska3/bin:${PATH}
cd /data/acis/ska3_pkg/src/acis_viols_tracking
make deploy 
