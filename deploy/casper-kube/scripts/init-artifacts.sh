#!/bin/bash
# set -e

ARTIFACTS_SOURCE_DIR=/shared/artifacts

function get_node_index() {
    echo "${CASPER_NODE_NAME}" | cut -d'-' -f3
}

function prerequisite_checks() {
    # shellcheck disable=2153
    if [ -z "${NETWORK_NAME}" ]
    then
        echo "NETWORK_NAME not set, exiting"
        exit 1
    fi

    if [ -z "${CASPER_NODE_NAME}" ]
    then
        if [ -z "${CASPER_NODE_PREFIX}" ]
        then
            CASPER_NODE_PREFIX=casper-node
        fi

        if [ -z "${CASPER_NODE_INDEX}" ]
        then
            echo "CASPER_NODE_INDEX not set, exiting"
            exit 1
        fi

        CASPER_NODE_NAME="${CASPER_NODE_PREFIX}-${CASPER_NODE_INDEX}"
    fi
    echo "${FUNCNAME[0]} complete"
}

function copy_initial_configs() {
	cp -r \
		"${ARTIFACTS_SOURCE_DIR}/nodes/${CASPER_NODE_NAME}/etc/casper" \
		/etc/
}

function copy_initial_binaries() {
    mkdir -p /var/lib/casper
	cp -r \
		"${ARTIFACTS_SOURCE_DIR}/staging/bin" \
		/var/lib/casper
}

function set_binary_permissions() {
	chmod +x /var/lib/casper/bin/1_0_0/casper-node
}

function main() {
    echo "Executing the ${BASH_SOURCE[0]} script in ${CASPER_NODE_NAME}"
    prerequisite_checks
    copy_initial_configs
    copy_initial_binaries
    set_binary_permissions
}

main
