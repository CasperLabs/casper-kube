#!/usr/bin/env bash
set -e

NETWORK_NAME_PREFIX="${1:-$NETWORK_NAME_PREFIX}"

function get_network_prefix() {
  if [[ -z "${NETWORK_NAME_PREFIX}" ]]; then
    whoami
  else
    echo "${NETWORK_NAME_PREFIX}"
  fi
}

function get_git_hash() {
  local casper_node_git_hash

  if [[ -d ../casper-node ]]; then
    (pushd ../casper-node/ || exit) > /dev/null 2>&1
  else
    >&2 echo "The casper-node directory seems to be missing"
    exit 1
  fi
  casper_node_git_hash="$(git rev-parse --short HEAD)"
  (popd || exit) > /dev/null 2>&1
  echo "${casper_node_git_hash}"
}

function get_network_suffix() {
  openssl rand -hex 2
}

NETWORK_PREFIX="$(get_network_prefix)"
GIT_HASH="$(get_git_hash)"
NETWORK_SUFFIX="$(get_network_suffix)"
NETWORK_NAME="${NETWORK_PREFIX}-${GIT_HASH}-${NETWORK_SUFFIX}"

if [[ "$( kubectl get namespaces | grep -c "${NETWORK_NAME}")" -gt 0 ]]; then
  >&2 echo "There is already a namespace for the given NETWORK_NAME_PREFIX"
  >&2 echo "Aborting attempt to create the network..."
  exit 1
fi

set +e
