#!/bin/bash

git clone https://github.com/CasperLabs/casper-node /casper-node
cd /casper-node
git checkout $CASPER_NODE_GIT_HASH

tail -f /dev/null
