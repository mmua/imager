#!/bin/bash
# see scripts/debian-init.d for production deployments

export PYTHONPATH=`dirname $0`
/usr/bin/twistd -l /var/log/imager/proxy.log --pidfile proxy.pid -n cyclone -p 8088 -l 127.0.0.1 \
       -r images.web.ProxyApplication -c images.conf $*
