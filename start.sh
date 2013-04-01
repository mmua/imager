#!/bin/bash
# see scripts/debian-init.d for production deployments

export PYTHONPATH=`dirname $0`
twistd -n cyclone -p 8087 -l 0.0.0.0 \
       -r images.web.Application -c images.conf $*
