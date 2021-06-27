#!/bin/bash
set -e

if [[ "${DEVELOPMENT_MODE}" == true ]]; then
    /scripts/init-artifacts.sh
fi

/var/lib/casper/bin/1_0_0/casper-node \
    validator \
    /etc/casper/1_0_0/config.toml \
    &

# #prevent the container from exiting even if casper-node exit's
tail -f /dev/null
