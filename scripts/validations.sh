#!/usr/bin/env bash
set -e

BOOTSTRAP_NODE_COUNT="${1:-$BOOTSTRAP_NODE_COUNT}"
DEVELOPMENT_MODE="${2:-$DEVELOPMENT_MODE}"
GENESIS_IN_SECONDS="${3:-$GENESIS_IN_SECONDS}"
IMAGE_TAG="${4:-$IMAGE_TAG}"
NETWORK_NAME_PREFIX="${5:-$NETWORK_NAME_PREFIX}"
NODE_NAME_PREFIX="${6:-$NODE_NAME_PREFIX}"
NODE_COUNT="${7:-$NODE_COUNT}"
NODE_MEM_LIMIT="${8:-$NODE_MEM_LIMIT}"
NODE_CPU_LIMIT="${9:-$NODE_CPU_LIMIT}"
NODE_STORAGE_CAPACITY="${10:-$NODE_STORAGE_CAPACITY}"
RWO_STORAGE_CLASS="${11:-$RWO_STORAGE_CLASS}"
RWM_STORAGE_CLASS="${12:-$RWM_STORAGE_CLASS}"

if ! which kubectl > /dev/null;
then
  >&2 echo "kubectl not installed"
  exit 1
fi

if ! which helm > /dev/null;
then
  >&2 echo "helm not installed"
  exit 1
fi

if ! kubectl get nodes > /dev/null;
then
  >&2 echo "kube auth not setup"
  exit 1
fi

if [ ! -d "../casper-node" ];
then
  >&2 echo "missing ../casper-node ; casper-node must be checked out in parent directory"
  exit 1
fi

if [ ! -f "../casper-node/target/release/casper-node" ];
then
  >&2 echo "build casper-node before running create-kube-network"
  exit 1
fi

if [ ! -d "../casper-node-launcher" ];
then
  >&2 echo "missing ../casper-node-launcher ; casper-node-launcher must be checked out in parent directory"
  exit 1
fi

if [ ! -f "../casper-node-launcher/target/release/casper-node-launcher" ];
then
  >&2 echo "build casper-node-launcher before running create-kube-network"
  exit 1
fi

if [ -z "${BOOTSTRAP_NODE_COUNT}" ]; then
  >&2 echo "BOOTSTRAP_NODE_COUNT variable is required"
  exit 1
fi

if [ -z "${DEVELOPMENT_MODE}" ]; then
  >&2 echo "DEVELOPMENT_MODE variable is required"
  exit 1
fi

if [ -z "${GENESIS_IN_SECONDS}" ]; then
  >&2 echo "GENESIS_IN_SECONDS variable is required"
  exit 1
fi

if [ -z "${IMAGE_TAG}" ]; then
  >&2 echo "IMAGE_TAG variable is required"
  exit 1
fi

if [ -z "${NETWORK_NAME_PREFIX}" ]; then
  >&2 echo "NETWORK_NAME_PREFIX variable is required"
  exit 1
fi

if [ -z "${NODE_NAME_PREFIX}" ]; then
  >&2 echo "NODE_NAME_PREFIX variable is required"
  exit 1
fi

if [ -z "${NODE_COUNT}" ]; then
  >&2 echo "NODE_COUNT variable is required"
  exit 1
fi

if [ -z "${NODE_MEM_LIMIT}" ]; then
  >&2 echo "NODE_MEM_LIMIT variable is required"
  exit 1
fi


if [ -z "${NODE_CPU_LIMIT}" ]; then
  >&2 echo "NODE_CPU_LIMIT variable is required"
  exit 1
fi

if [ -z "${NODE_STORAGE_CAPACITY}" ]; then
  >&2 echo "NODE_STORAGE_CAPACITY variable is required"
  exit 1
fi

if [ -z "${RWO_STORAGE_CLASS}" ]; then
  >&2 echo "RWO_STORAGE_CLASS variable is required"
  exit 1
fi


if [ -z "${RWM_STORAGE_CLASS}" ]; then
  >&2 echo "RWM_STORAGE_CLASS variable is required"
  exit 1
fi

set +e
