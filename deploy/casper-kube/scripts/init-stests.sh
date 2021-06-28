#!/bin/bash
set -e

ARTIFACTS_SOURCE_DIR=/shared/artifacts

if [[ "${DEVELOPMENT_MODE}" == true ]]; then

    # shellcheck disable=2153
    if [ -z "${NETWORK_NAME}" ]
    then
        echo "NETWORK_NAME not set, exiting"
        exit 1
    fi

    mkdir -p /root/.casperlabs-stests/nets/kubenet

    cp -rT \
        "${ARTIFACTS_SOURCE_DIR}/stests_net" \
        /root/.casperlabs-stests/nets/kubenet
fi

service redis-server start

#prevent the container from exiting even if casper-node exit's
tail -f /dev/null
