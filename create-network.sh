#!/bin/bash
set -e

network_name=$1
git_rev=$2
node_count=$3


node_mem_limit="600Mi"
node_mem_request="200Mi"
node_cpu_limit="500m"
node_cpu_request="100m"


namespace="${network_name}"
network_resources_yaml="/tmp/${namespace}.yaml"


#####################################################################################################################
# Upload build artifacts to S3 Bucket
#####################################################################################################################


#####################################################################################################################
# Create Kubernetes Resources
#####################################################################################################################

echo "------------------------------------------------"
echo "Creating network in namespace $namespace"
echo "------------------------------------------------"
echo ""
echo "Network Name: $network_name"
echo "Build git rev: $git_rev"
echo ""
echo "writing $network_resources_yaml"

for index in $(seq 1 $node_count)
do

zero_pad_index=$(printf %03d $index)
node_label="casper-node-$zero_pad_index"

cat << EOF >> $network_resources_yaml
#
# $node_label
#

---
kind: Pod
apiVersion: v1
metadata:
  name: $node_label
  labels:
    app: $node_label
spec:
  containers:
    - name: $node_label
      image: 878804750492.dkr.ecr.us-east-2.amazonaws.com/casper-kube-node
      env:
      - name: CASPER_NODE_GIT_REV
        value: "$git_rev"
      - name: CASPER_NODE_INDEX
        value: "$zero_pad_index"
      - name: NETWORK_NAME
        value: "$network_name"        
      - name: RUST_LOG
        value: info
      - name: RUST_BACKTRACE
        value: "1"
      resources:
        limits:
          cpu: "$node_cpu_limit"
          memory: "$node_mem_limit"
        requests:
          cpu: "$node_cpu_request"
          memory: "$node_mem_request"


---
kind: Service
apiVersion: v1
metadata:
  name: $node_label
spec:
  selector:
    app: $node_label
  ports:
    - name: rest
      protocol: TCP
      port: 8888
      targetPort: 8888
    - name: rpc
      protocol: TCP
      port: 7777
      targetPort: 7777
    - name: casper-node
      protocol: TCP
      port: 34553
      targetPort: 34553      
EOF

done

cat << EOF >> $network_resources_yaml

---
kind: Pod
apiVersion: v1
metadata:
  name: casper-util
spec:
  containers:
  - image: 878804750492.dkr.ecr.us-east-2.amazonaws.com/casper-kube-util
    env:
    - name: CASPER_NODE_GIT_REV
      value: "$git_rev"
    name: casper-network-util
  restartPolicy: Always
EOF


#####################################################################################################################
# Apply Kubernetes Resources
#####################################################################################################################

kubectl create namespace $namespace
kubectl apply -n $namespace -f $network_resources_yaml
