#!/usr/bin/env bash
set -e

RWO_STORAGE_CLASS="${1:-gp2}"
HELM_VALUES_PATH="${2:-nfs-values.yaml}"

# See
# https://artifacthub.io/packages/helm/kvaps/nfs-server-provisioner
# https://github.com/kubernetes-sigs/nfs-ganesha-server-and-external-provisioner/tree/master/deploy/helm
helm repo add kvaps https://kvaps.github.io/charts

if [[ -z "$(kubectl get storageclass nfs-retain 2>/dev/null || true)" ]]; then
  helm install nfs-server-provisioner-retain kvaps/nfs-server-provisioner \
    --namespace="nfs-server-provisioner-retain" \
    --create-namespace \
    --atomic \
    --values="${HELM_VALUES_PATH}" \
    --set persistence.storageClass="${RWO_STORAGE_CLASS}" \
    --set storageClass.reclaimPolicy=Retain \
    --set storageClass.name=nfs-retain &&
  echo "nfs retain storageclass installation successful"
fi

if [[ -z "$(kubectl get storageclass nfs 2>/dev/null || true)" ]]; then
  helm install nfs-server-provisioner kvaps/nfs-server-provisioner \
    --namespace="nfs-server-provisioner" \
    --create-namespace \
    --atomic \
    --values="${HELM_VALUES_PATH}" \
    --set persistence.storageClass="${RWO_STORAGE_CLASS}" \
    --set storageClass.reclaimPolicy=Delete \
    --set storageClass.name=nfs &&
  echo "nfs storageclass installation successful"
fi