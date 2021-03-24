#!/bin/bash

#stests network
#https://github.com/CasperLabs/stests/blob/master/docs/usage_lrt.md

bucket_name="builds.casperlabs.io"
aws s3 sync s3://$bucket_name/networks/$NETWORK_NAME/stests_net/ /root/.casperlabs-stests/nets/kubenet/

service redis-server start 
tail -f /dev/null
