#!/bin/bash

/var/lib/casper/bin/1_0_0/casper-node \
    validator \
    /etc/casper/1_0_0/config.toml \
    &

tail -f /dev/null
