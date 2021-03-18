#!/bin/bash

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

./casper-tool.py create-network --genesis-in 300 artifacts/$network_name
aws s3 sync artifacts/$network_name s3://builds.casperlabs.io/networks/$network_name


./create-network.sh $network_name $git_hash 5
