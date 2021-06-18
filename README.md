# casper-kube

A kubernetes statefulset driven casper network intended for development
and or integration tests.

Generates a network on Kubernetes using your the current
binaries from a local casper-node project.

Can facilitate a network of arbitary size in terms of the
number of pods and CPU/Memory resources requested.

Can be run in `development_mode` in which case binaries and configurations
from the developers local laptop will be uploaded to the kubernetes environment
facilitating testing changes being made locally on a large sized network beyond
which the [nctl](https://github.com/casper-network/casper-node/blob/master/utils/nctl/README.md)
tool is capable.

## Prerequisites

### Basic Requirements

* A kubernetes cluster with sufficient capacity to support the
network and ideally node autoscaling capabilities enabled. Exact resource
requirements depend on the size of network generated.

* A kubeconfig file granting access to the kubernetes cluster.

* [Kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl)

* [Helm](https://helm.sh/docs/intro/install)

* [Dasel](https://daseldocs.tomwright.me/installation) for building
the `kube-hosts.yaml` file with an arbitrary number of pods

### Development Mode Requirements

* Availability in cluster of a ReadWriteMany storageclass available within the cluster. If
a ReadWriteMany storageclass is unavailable, then one can be created by deploying
a `nfs-server-provisioner`. The [install_nfs_provisioner script](./scripts/install_nfs_provisioner.sh) 
can be used to deploy a `nfs-server-provisioner`. More information about available storageclasses 
can be found [in the kubernetes docs](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes).

* [Devspace](https://devspace.cloud/docs/cli/getting-started/installation)
for copying local files to k8s.

### Optional tools

* [Lens](https://k8slens.dev/)

## Usage

### Development Mode

#### Generate the binaries

Clone the required casperlab github repositories at the same directory
tree level.

```bash
git clone https://github.com/CasperLabs/casper-kube.git
git clone https://github.com/casper-network/casper-node.git
git clone https://github.com/casper-network/casper-node-launcher.git
```

Checkout the required version for local development purposes and then
make the code changes of interest. Example below.

```bash
pushd casper-node
git fetch origin && git checkout dev
popd
```

Once the necessary code changes are made, build the
casper binaries locally. The following block of code builds
the binaries for

* [casper-node-launcher](https://github.com/casper-network/casper-node-launcher)
* [casper-client](https://github.com/casper-network/casper-node/tree/master/client)
* [casper-node](https://github.com/casper-network/casper-node/tree/master/node)

```bash
pushd casper-node-launcher || >&2 echo "casper-node-launcher dir expected"
cargo build --release
popd

pushd casper-node || >&2 echo "casper-node dir expected"
cargo build --release --package casper-client
cargo build --release --package casper-node
popd
```

#### Deploy the Network

```bash
./create-kube-network \
  --bootstrap_node_count 3 \
  --development_mode true \
  --genesis_in_seconds 1200 \
  --image_tag latest \
  --network_name_prefix mynet \
  --node_name_prefix casper-node \
  --node_count 7 \
  --node_cpu 500m \
  --node_mem 500Mi \
  --node_storage_capacity 1Gi \
  --rwo_storage_class gp2 \
  --rwm_storage_class nfs \
  --validator_node_count 2 \
  --zero_weight_node_count 2
```

### Deleting the Network

This can be achieved by deleting the network namespace
in the kubernetes cluster and artifacts in the local
`./artifacts` directory.

## Network Inspection

### View network in Lens

Navigate to `Workloads -> Pods` and selected the generated network from the Namespace dropdown menu. eg. `rob-cb1d20ad-c6ed`

![Lens example](docs/readme1.png)

### View logs / Get Shell / Monitoring

Use Pod context menu (top right shelf icons)

![Lens example](docs/readme2.png)

### View logs in Kibana

`create-kube-network` will output a link to Kibana with logs scoped to the newly created network

![Kibana Logs](docs/readme3.png)

## License

[Apache 2.0](./LICENSE)
