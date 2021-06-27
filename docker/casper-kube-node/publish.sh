#!/bin/bash
set -xe

DOCKER_REPO_NAME=casper-kube-node
DOCKER_REPO_HOST=878804750492.dkr.ecr.us-east-2.amazonaws.com
DOCKER_URI="${DOCKER_REPO_HOST}/${DOCKER_REPO_NAME}"

sudo docker build . -t "${DOCKER_REPO_NAME}:latest"
aws ecr get-login-password --region us-east-2 | sudo docker login --username AWS --password-stdin $DOCKER_REPO_HOST
sudo docker tag $DOCKER_REPO_NAME:latest $DOCKER_URI:latest
sudo docker push $DOCKER_URI:latest
