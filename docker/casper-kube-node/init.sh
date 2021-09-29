#!/bin/bash

bucket_name="builds.casperlabs.io"


if [ -z "$NETWORK_NAME" ]
then
    echo "NETWORK_NAME not set, exiting"
    exit 1
fi


if [ -z "$CASPER_NODE_INDEX" ]
then
    echo "CASPER_NODE_INDEX not set, exiting"
    exit 1
fi

if [ -z "$CASPER_NODE_VERSION" ]
then
    echo "CASPER_NODE_VERSION not set, exiting"
    exit 1
fi

#ensure the bootstrap node has started, before bringing up our node
#if [ ! $CASPER_NODE_INDEX == "001" ]; 
#then 
#    echo "sleeping for 30 seconds to ensure bootstrap node has started"
#    sleep 30
#fi

#config
echo "aws s3 sync s3://${bucket_name}/networks/${NETWORK_NAME}/nodes/casper-node-${NETWORK_NAME}-${CASPER_NODE_INDEX}/etc/ /etc/"
aws s3 sync s3://$bucket_name/networks/$NETWORK_NAME/nodes/casper-node-${NETWORK_NAME}-${CASPER_NODE_INDEX}/etc/ /etc/

#binary
aws s3 sync s3://$bucket_name/networks/$NETWORK_NAME/staging/bin /var/lib/casper/bin
chmod +x /var/lib/casper/bin/$CASPER_NODE_VERSION/casper-node

ls /etc/casper

bash -c "exec /usr/bin/casper-node-launcher"
