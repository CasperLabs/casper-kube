#!/bin/bash
set -xe 

DOCKER_REPO_NAME=casper-kube-util
DOCKER_REPO_HOST=878804750492.dkr.ecr.us-east-2.amazonaws.com
DOCKER_URI="${DOCKER_REPO_HOST}/${DOCKER_REPO_NAME}"

aws ecr get-login-password --region us-east-2 | sudo docker login --username AWS --password-stdin $DOCKER_REPO_HOST

sudo docker build . -t "${DOCKER_REPO_NAME}:latest"
sudo docker tag $DOCKER_REPO_NAME $DOCKER_URI
sudo docker push $DOCKER_URI
