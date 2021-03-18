#!/bin/bash

bucket_url=http://builds.casperlabs.io
arch=`arch`


if [ -z "$CASPER_NODE_GIT_REV" ]
then
    echo "CASPER_NODE_GIT_REV not set, exiting"
    exit 1
fi


if [ -z "$CASPER_NODE_INDEX" ]
then
    echo "CASPER_NODE_INDEX not set, exiting"
    exit 1
fi

network_name=$NETWORK_NAME



mkdir /storage
#mkdir /config

#binary
#curl $bucket_url/$CASPER_NODE_GIT_REV/build/$arch/casper-node -o /usr/bin/casper-node
aws s3 sync s3://builds.casperlabs.io/networks/$network_name/staging/bin /var/lib/casper/bin
chmod +x /var/lib/casper/bin/1_0_0/casper-node

#marc casper-tool
#node_config="$bucket_url/$network-name/node-$CASPER_NODE_INDEX/"
#aws s3 sync s3://builds.casperlabs.io/networks/$network_name/node-$CASPER_NODE_INDEX /config/node
#aws s3 sync s3://builds.casperlabs.io/networks/$network_name/chain /config/chain
#cd /config/node #relative paths as per config.toml 
#/usr/bin/casper-node validator /config/node/config.toml &


#danw casper-tool
#node_config="$bucket_url/networks/$network_name/nodes/node-$CASPER_NODE_INDEX"

aws s3 sync s3://builds.casperlabs.io/networks/$network_name/nodes/casper-node-$CASPER_NODE_INDEX/etc/ /etc/

#/usr/bin/casper-node validator /etc/casper/1_0_0/config.toml &
/var/lib/casper/bin/1_0_0/casper-node validator /etc/casper/1_0_0/config.toml &






tail -f /dev/null

