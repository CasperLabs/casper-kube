#!/usr/bin/env bash
# See https://github.com/CasperLabs/stests/blob/master/docs/usage_lrt.md
set -e

GENESIS_IN_SECONDS="${1:-$GENESIS_IN_SECONDS}"
NETWORK_NAME="${2:-$NETWORK_NAME}"

echo "--------------------------------------------------"
echo "running casper-tool:"

./casper-tool.py create-network \
  --genesis-in "${GENESIS_IN_SECONDS}" \
  --hosts-file kube-hosts.yaml \
  artifacts/"${NETWORK_NAME}"

pushd artifacts/"${NETWORK_NAME}" || exit

mkdir stests_net
mkdir stests_net/configs
mkdir stests_net/faucet
mkdir stests_net/bin

cp staging/config/chainspec.toml stests_net/
cp staging/config/accounts.toml stests_net/
cp staging/faucet/secret_key.pem stests_net/faucet
cp staging/bin/casper-client stests_net/bin

pushd ./nodes || exit
for node in *;
do
  mkdir -p ../stests_net/configs/"${node}"
  cp "${node}"/etc/casper/keys/secret_key.pem ../stests_net/configs/"${node}"/
done

popd || exit
popd || exit

set +e
