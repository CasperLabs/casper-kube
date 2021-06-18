#!/usr/bin/env bash
set -e

NETWORK_NAME="${1:-$NETWORK_NAME}"
NODE_NAME_PREFIX="${2:-$NODE_NAME_PREFIX}"
HELM_CHART_NAME="${3:-$HELM_CHART_NAME}"

function get_pod_name() {
  local namespace="${1}"
  local pod_selector="${2}"

  kubectl get pods \
    --namespace "${namespace}" \
    --selector "${pod_selector}" \
    -o name 2>/dev/null |
    awk 'NR==1' |
    cut -d'/' -f2 ||
    true
}

function get_pod_status() {
  local namespace="${1}"
  local pod_name="${2}"

  kubectl get pods "${pod_name}" \
     --namespace "${namespace}" \
     -o json |
     jq -r .status.phase 2>/dev/null || true
}

function get_container_status() {
  local namespace="${1}"
  local pod_name="${2}"

  kubectl get pods "${pod_name}" \
     --namespace "${namespace}" \
     --output "json" |
     jq -r '.status.containerStatuses[0].state | keys[0]' \
     2>/dev/null || true
}

function get_sync_pod() {
  local namespace="${1}"
  local selector="${2}"

  # Waiting for the artifacts sync job to be started
  while [[ -z "$(get_pod_name "${namespace}" "${selector}")" ]]; do
    sleep 10s
  done
  get_pod_name "${namespace}" "${selector}"
}

function wait_for_sync_deployment() {
  local namespace="${1}"
  local sync_pod="${2}"

  while [[ -z "$(get_pod_status "${namespace}" "${sync_pod}")" ]]; do
    echo "Waiting for pod ${sync_pod} lifecycle to start"
    sleep 10s
  done
  echo "status of pod ${sync_pod}: $(get_pod_status "${namespace}" "${sync_pod}")"

  while [[ -z "$(get_container_status "${namespace}" "${sync_pod}")" ]] ||
        [[ "$(get_container_status "${namespace}" "${sync_pod}")" != "running" ]]; do
    echo "Waiting for pod ${sync_pod} container to be running"
    sleep 10s
  done

  echo "containerStatuses[0] container status of ${sync_pod}: \
    $(get_container_status "${namespace}" "${sync_pod}")"
}

function upload_artifacts() {
  local namespace="${1}"
  local local_path="${2}"
  local job_selector="${3}"
  local container_name="${4}"

  devspace sync \
    --namespace "${namespace}" \
    --local-path "${local_path}" \
    --container-path /shared/artifacts \
    --label-selector "${job_selector}" \
    --container "${container_name}" \
    --no-warn \
    --no-watch \
    --upload-only \
    --verbose

  if [[ ! -d artifacts/"${NETWORK_NAME}"/done ]]; then
    mkdir -p artifacts/"${NETWORK_NAME}"/done
    touch artifacts/"${NETWORK_NAME}"/done/done.txt
  fi &&

  devspace sync \
    --namespace "${namespace}" \
    --local-path "${local_path}/done" \
    --container-path /shared/artifacts/done \
    --label-selector "${job_selector}" \
    --container "${container_name}" \
    --no-warn \
    --no-watch \
    --upload-only \
    --verbose
}

if [[ "${DEVELOPMENT_MODE}" == "true" ]]; then
    SYNC_POD="$(get_sync_pod "${NETWORK_NAME}" "job-name=${NODE_NAME_PREFIX}-artifacts")"

    wait_for_sync_deployment "${NETWORK_NAME}" "${SYNC_POD}" &&
      (
        echo "Commencing upload of artifacts/${NETWORK_NAME} to ${SYNC_POD}"
        upload_artifacts \
            "${NETWORK_NAME}" \
            "${PWD}/artifacts/${NETWORK_NAME}" \
            "job-name=${NODE_NAME_PREFIX}-artifacts"
            "${HELM_CHART_NAME}"
        echo "artifacts/${NETWORK_NAME} upload to ${SYNC_POD} is complete"
      )
fi

sleep 3s

set +e
