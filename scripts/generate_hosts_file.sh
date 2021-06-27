#!/usr/bin/env bash
set -e

NODE_NAME_PREFIX="${1:-$NODE_NAME_PREFIX}"
NODE_COUNT="${2:-$NODE_COUNT}"
BOOTSTRAP_NODE_COUNT="${3:-$BOOTSTRAP_NODE_COUNT}"
VALIDATOR_NODE_COUNT="${4:-VALIDATOR_NODE_COUNT}"
ZERO_WEIGHT_NODE_COUNT="${5:-ZERO_WEIGHT_NODE_COUNT}"

function generate_hosts_file() {
  local node_name_prefix="${1:-casper-node}"
  local nodes="${2:-5}"
  local bootstrap_nodes="${3}"
  local validator_nodes="${4}"
  local zero_weight_nodes="${5}"
  local remaining_nodes
  local calculated_sum_of_nodes

  if [[ -z "${bootstrap_nodes}" ]]; then
    echo "Setting the number of bootstrap_nodes to default of 1"
    bootstrap_nodes=1
  fi

  local remaining_nodes="$(("${nodes}"-"${bootstrap_nodes}"))"

  if [[ -z "${validator_nodes}" ]]; then
    local default_validator_nodes
    default_validator_nodes="$(("${remaining_nodes}"/2))"
    echo "Setting the number of validator_nodes to default of ${default_validator_nodes}"
    validator_nodes="${default_validator_nodes}"
  fi

  local remaining_nodes="$(("${nodes}"-"${validator_nodes}"-"${bootstrap_nodes}"))"

  if [[ -z "${zero_weight_nodes}" ]]; then
    zero_weight_nodes="${remaining_nodes}"
  fi

  calculated_sum_of_nodes="$(("${zero_weight_nodes}"+"${validator_nodes}"+"${bootstrap_nodes}"))"

  if [[ "${nodes}" != "${calculated_sum_of_nodes}" ]]; then
    >&2 echo "The total number of nodes must be equal to the calculated sum of nodes"
    exit 1
  fi

  cp "${PWD}"/kube-hosts-template.yaml "${PWD}"/kube-hosts.yaml

  local bootstrap_nodes_sequence_step
  local validator_nodes_sequence_step
  local zero_weight_sequence_step
  bootstrap_nodes_sequence_step="$(("${bootstrap_nodes}"-1))"
  validator_nodes_sequence_step="$(("${bootstrap_nodes_sequence_step}"+"${validator_nodes}"))"
  zero_weight_sequence_step="$(("${validator_nodes_sequence_step}"+"${zero_weight_nodes}"))"

  local bootstrap_node_type_args
  local validator_node_type_args
  local zero_weight_node_type_args
  local bootstrap_node_kv_args
  local validator_node_kv_args
  local zero_weight_node_kv_args

  for node_index in $(seq 0 "${bootstrap_nodes_sequence_step}"); do
    bootstrap_node_type_args="${bootstrap_node_type_args} -t string"
    bootstrap_node_kv_args="${bootstrap_node_kv_args} ${node_name_prefix}-${node_index}="
  done

  # shellcheck disable=2086
  dasel put object \
    -f "${PWD}"/kube-hosts.yaml \
    ${bootstrap_node_type_args} \
    -s "all.children.bootstrap.hosts" \
    ${bootstrap_node_kv_args}

  for node_index in $(seq "$((bootstrap_nodes_sequence_step+1))" "${validator_nodes_sequence_step}"); do
    validator_node_type_args="${validator_node_type_args} -t string"
    validator_node_kv_args="${validator_node_kv_args} ${node_name_prefix}-${node_index}="
  done

  # shellcheck disable=2086
  dasel put object \
    -f "${PWD}"/kube-hosts.yaml \
    ${validator_node_type_args} \
    -s "all.children.validators.hosts" \
    ${validator_node_kv_args}

  for node_index in $(seq "$((validator_nodes_sequence_step+1))" "${zero_weight_sequence_step}"); do
    zero_weight_node_type_args="${zero_weight_node_type_args} -t string"
    zero_weight_node_kv_args="${zero_weight_node_kv_args} ${node_name_prefix}-${node_index}="
  done

  # shellcheck disable=2086
  dasel put object \
    -f "${PWD}"/kube-hosts.yaml \
    ${zero_weight_node_type_args} \
    -s "all.children.zero_weight.hosts" \
    ${zero_weight_node_kv_args}
}

echo "--------------------------------------------------"
echo "Generating kube-hosts.yaml file"

generate_hosts_file \
  "${NODE_NAME_PREFIX}" \
  "${NODE_COUNT}" \
  "${BOOTSTRAP_NODE_COUNT}" \
  "${VALIDATOR_NODE_COUNT}" \
  "${ZERO_WEIGHT_NODE_COUNT}"

echo "--------------------------------------------------"
echo "Displaying the generated kube-hosts.yaml file"
cat "${PWD}"/kube-hosts.yaml

set +e
