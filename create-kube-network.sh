#!/bin/bash

node_count=5
node_mem_limit="600Mi"
node_mem_request="200Mi"
node_cpu_limit="500m"
node_cpu_request="100m"

docker_repository="878804750492.dkr.ecr.us-east-2.amazonaws.com"
build_bucket="builds.casperlabs.io"
genesis_in_seconds=300

######################################################
# sanity checks 
######################################################

if ! which aws > /dev/null;
then
  echo "awscli utilities not installed"
  exit 1
fi

if ! aws sts get-caller-identity > /dev/null;
then
  echo "aws credentials not setup"
  exit 1
 fi

if ! which kubectl > /dev/null;
then
  echo "kubectl not installed"
  exit 1
fi

if [ ! -d "../casper-node" ];
then
  echo "missing ../casper-node ; casper-node must be checked out in parent directory"
fi

if [ ! -d "../casper-node-launcher" ];
then
  echo "missing ../casper-node-launcher ; casper-node-launcher must be checked out in parent directory"
fi


######################################################
# uniquely name network
######################################################

git_hash=`cd ../casper-node/; git rev-parse --short HEAD`
user=`whoami`
random=`openssl rand -hex 2`
network_name="${user}-${git_hash}-${random}"


######################################################
# generate casper-tool artifacts and sync to s3
######################################################

./casper-tool.py create-network --genesis-in $genesis_in_seconds --hosts-file kube-hosts.yaml artifacts/$network_name
aws s3 sync artifacts/$network_name s3://$build_bucket/networks/$network_name



#####################################################################################################################
# Create Kubernetes Resources
#####################################################################################################################

namespace="${network_name}"
kube_resources_yaml="./artifacts/${network_name}/kube_resources.yaml"

echo "------------------------------------------------"
echo "Creating network in namespace $namespace"
echo "------------------------------------------------"
echo ""
echo "Network Name: $network_name"
echo "Build git rev: $git_hash"
echo ""
echo "writing $kube_resources_yaml"

for index in $(seq 1 $node_count)
do

zero_pad_index=$(printf %03d $index)
node_label="casper-node-$zero_pad_index"

cat << EOF >> $kube_resources_yaml
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
      image: "${docker_repository}/casper-kube-node"
      env:
      - name: CASPER_NODE_GIT_REV
        value: "$git_hash"
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

cat << EOF >> $kube_resources_yaml

---
kind: Pod
apiVersion: v1
metadata:
  name: casper-util
spec:
  containers:
  - image: "${docker_repository}/casper-kube-util"
    env:
    - name: CASPER_NODE_GIT_HASH
      value: "$git_hash"
    name: casper-network-util
  restartPolicy: Always
EOF


#####################################################################################################################
# Apply Kubernetes Resources
#####################################################################################################################

kubectl create namespace $namespace
kubectl apply -n $namespace -f $kube_resources_yaml

