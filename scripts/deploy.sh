#!/usr/bin/env bash
set -e

NETWORK_NAME="${1:-$NETWORK_NAME}"
NODE_NAME_PREFIX="${2:-$NODE_NAME_PREFIX}"
DEVELOPMENT_MODE="${3:-$DEVELOPMENT_MODE}"
NODE_COUNT="${4:-$NODE_COUNT}"
NODE_STORAGE_CAPACITY="${5:-$NODE_STORAGE_CAPACITY}"
RWO_STORAGE_CLASS="${6:-RWO_STORAGE_CLASS}"
RWM_STORAGE_CLASS="${7:-RWM_STORAGE_CLASS}"
NODE_MEM_LIMIT="${8:-$NODE_MEM_LIMIT}"
NODE_CPU_LIMIT="${9:-$NODE_CPU_LIMIT}"
IMAGE_TAG="${10:-$IMAGE_TAG}"

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

function create_network() {
  echo "--------------------------------------------------"
  echo "Deploying network in namespace ${NETWORK_NAME}"
  echo "--------------------------------------------------"
  echo ""
  echo "Network Name: ${NETWORK_NAME}"
  echo "Build git rev: $(get_git_hash)"
  echo ""

  helm install "${NODE_NAME_PREFIX}" \
    --wait=false \
    --wait-for-jobs=false \
    --create-namespace \
    --namespace="${NETWORK_NAME}" \
    --set developmentMode="${DEVELOPMENT_MODE}" \
    --set gitHash="$(get_git_hash)" \
    --set network_name="${NETWORK_NAME}" \
    --set replicaCount="${NODE_COUNT}" \
    --set volumeClaimSize="${NODE_STORAGE_CAPACITY}" \
    --set volumeStorageClass="${RWO_STORAGE_CLASS}" \
    --set artifactsVolumeStorageClass="${RWM_STORAGE_CLASS}" \
    --set resources.limits.memory="${NODE_MEM_LIMIT}" \
    --set resources.limits.cpu="${NODE_CPU_LIMIT}" \
    --set image.tag="${IMAGE_TAG}" \
    ./deploy/casper-kube

  echo ""
  echo "Network creation complete."
  echo ""
}

create_network

set +e
