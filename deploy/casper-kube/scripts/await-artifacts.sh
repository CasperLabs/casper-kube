#!/bin/bash
set -e

ARTIFACTS_SOURCE_DIR=/shared/artifacts

function calc_unix_time() {
    local minutes_from_now="${1:-0}"

    date --utc --date="${minutes_from_now}minutes" +%s
}

function prerequisite_checks() {
    # shellcheck disable=2153
    if [[ -z "${NETWORK_NAME}" ]]
    then
        echo "NETWORK_NAME not set, exiting"
        exit 1
    fi
    echo "${FUNCNAME[0]} complete"
}

# Places the init container in a holding pattern until shared artifacts are ready
function wait_for_network_artifacts() {
    local max_waiting_time="${1:-5}"
    local artifacts_source_dir="${2:-}"
    local current_time
    local forced_termination_time

    forced_termination_time="$(calc_unix_time "${max_waiting_time}")"

    while [[ ! -e "${artifacts_source_dir}"/done/done.txt ]]; do
        echo "Waiting for the shared network artifacts to be uploaded"
        # shellcheck disable=2034
        for dot in $(seq 1 10); do
            echo -ne '.'
            sleep 1s
        done
        echo ""
        current_time="$(calc_unix_time 0)"
        if [[ "${current_time}" -gt "${forced_termination_time}" ]]; then
            >&2 echo "Max threshold of ${max_waiting_time} minutes exceeded."
            >&2 echo "Aborting wait for network artifact files."
            exit 1
        else
            echo "Continuing to wait for shared network artifacts..."
        fi
    done
    echo "${FUNCNAME[0]} complete"
}

function main() {
    if [[ ! -d "${ARTIFACTS_SOURCE_DIR}" ]]; then
        mkdir -p "${ARTIFACTS_SOURCE_DIR}"
    fi
    prerequisite_checks
    wait_for_network_artifacts 5 "${ARTIFACTS_SOURCE_DIR}"
    echo "${FUNCNAME[0]} complete"
}

main
