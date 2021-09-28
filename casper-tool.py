#!/usr/bin/env python3

from datetime import datetime, timedelta
import os
import subprocess
import click
import shutil
from click.types import STRING
import toml
import yaml
import json
import tarfile
from pathlib import Path
import boto3
import requests
import tarfile, io

@click.group()
@click.option(
    "--casper-client",
    help="path to casper client binary downloaded by default",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    default="./usr/bin/casper-client",
)
@click.option(
    "-P",
    "--node-port",
    type=int,
    default=35000,
    help="Node Port for Network (default='35000')",
)
@click.option(
    "--validator-count",
    type=int,
    default=5,
    help="Number of Validators",
)
@click.option(
    "--non-validator-count",
    type=int,
    default=2,
    help="Number of Non Validators",
)
@click.pass_context
def cli(
    ctx,
    casper_client,
    node_port,
    validator_count,
    non_validator_count,
):
    """Casper Network creation tool

    Can be used to create new casper-labs chains with automatic validator setups. Useful for testing."""
    obj = {}

    obj["casper_client_argv0"] = [casper_client]
    obj["validator-node-count"] = validator_count
    obj["zero-weight-node-count"] = non_validator_count
    obj["casper-node-port"] = node_port

    ctx.obj = obj
    return

## ADD JOINER
##
@cli.command("add-joiners")
@click.pass_obj
@click.argument("target-path", type=click.Path(exists=False, writable=True), default="artifacts/chain-1")
@click.option(
    "-k",
    "--hosts-file",
    help="Parse an hosts.yaml file, using all.children.validators for set of known nodes",
    default="aws-hosts.yaml"
)
@click.option(
    "-n",
    "--network-name",
    help="The network name (also set in chainspec), defaults to output directory name",
)
@click.option(
    "-v",
    "--node-version",
    type=str,
    help="semver with underscores e.g. 1_0_0",
    default="1_0_0"
)
@click.option(
    "-j",
    "--trusted-hash",
    type=str,
    help="trusted hash with which to join",
)
def add_joiners(
    obj,
    target_path,
    hosts_file,
    network_name,
    node_version,
    trusted_hash
):
    if not network_name:
        network_name = os.path.basename(os.path.join(target_path))

    # Create the network output directories.
    show_val("Output path", target_path)

    nodes_path = \
        os.path.join(target_path, "nodes")

    staging_path = os.path.join(target_path, "staging")
    bin_path = \
        os.path.join(staging_path, "bin")
    bin_version_path = \
        os.path.join(staging_path, "bin", node_version)
    config_path = \
        os.path.join(staging_path, "config")

    # Staging directories for config, chain
    show_val("Node version", node_version)

    # Pull existing chainspec from staging dir
    chainspec_path = os.path.join(config_path, "chainspec.toml")
    show_val("Chainspec", chainspec_path)

    # Copy casper-node into bin/VERSION/ staging dir
    node_bin_path = os.path.join(bin_version_path, "casper-node")
    os.chmod(node_bin_path, 0o744)

    show_val("Creating binary archive", "bin.tar.bz2")
    with tarfile.open(os.path.join(staging_path, "bin.tar.bz2"), "w:bz2") as tar:
        tar.add(bin_path, arcname=os.path.basename(bin_path))

    faucet_path = os.path.join(staging_path, "faucet")

    # Load validators from ansible yaml inventory
    hosts = yaml.load(open(hosts_file), Loader=yaml.FullLoader)
    #osts = hosts_json
    config_template = os.path.join(config_path, "config-example.toml")
    show_val("Node config template", config_template)

    joining_nodes = list(hosts["all"]["children"]["joiners"]["hosts"].keys())
    validator_nodes = list(hosts["all"]["children"]
                           ["validators"]["hosts"].keys())
    bootstrap_nodes = list(hosts["all"]["children"]
                           ["bootstrap"]["hosts"].keys())

    for public_address in joining_nodes:
        show_val("adding joining node", public_address)
        generate_node_config(validator_nodes + bootstrap_nodes, config_template, obj,
                      nodes_path, node_version, public_address, trusted_hash)
        node_path = os.path.join(nodes_path, public_address)

        show_val("copying files to ", node_path)

        # copy the bin and chain into each node's versioned fileset
        node_var_lib_casper = os.path.join(node_path, "var", "lib", "casper")
        Path(node_var_lib_casper).mkdir(parents=True, exist_ok=True)
        node_config_path = \
            os.path.join(node_path, "etc", "casper", node_version)
        node_key_path = os.path.join(node_path, "etc", "casper", "keys")
        generate_account_key(node_key_path, public_address, obj)

        # copy the faucet's secret_key.pem into each node's config
        faucet_target_path = os.path.join(node_key_path, "faucet")
        Path(faucet_target_path).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            os.path.join(faucet_path, "secret_key.pem"),
            os.path.join(faucet_target_path, "secret_key.pem")
        )

        for filename in os.listdir(config_path):
            shutil.copyfile(
                os.path.join(config_path, filename),
                os.path.join(node_config_path, filename)
            )


## PUBLISH NETWORK ARTIFACTS
##
@cli.command("publish-network")
@click.pass_obj
@click.argument("target-path", type=click.Path(exists=False, writable=True), default="artifacts/chain-1")
@click.option(
    "-n",
    "--network-name",
    help="The network name (also set in chainspec), defaults to output directory name",
)
@click.option(
    "--aws-profile",
    type=STRING,
    default="default",
    help="AWS Profile from AWS Credentials",
)
@click.option(
    "--target-s3-bucket",
    type=STRING,
    default="builds.casperlabs.io",
    help="AWS S3 Bucket to Publish Network Artifacts",
)
@click.option(
    "--node-version",
    type=STRING,
    default="1_0_0",
    help="Release Node Version (default=1_0_0)",
)
# create network
def publish_network(
    obj,
    target_path,
    target_s3_bucket,
    aws_profile,
    network_name,
    node_version
):

    if not network_name:
        network_name = os.path.basename(os.path.join(target_path))

    try:
        # publish to target url (aws s3)
        if target_s3_bucket:

            show_val("AWS S3 Bucket", target_s3_bucket)
            session = None
            if aws_profile=="None":
                session = boto3.session.Session()
            else:
                session = boto3.session.Session(profile_name=aws_profile)
            s3 = session.client('s3')

            for path, subdirs, files in os.walk(target_path):
                directory_name = path.replace(target_path, "")
                directory_name = directory_name[:0] + directory_name[0+1:]
                for file in files:
                    with open(os.path.join(path, file), "rb") as f:                       
                        fileObj = os.path.join('networks', network_name, os.path.join(directory_name, file))
                        s3.upload_fileobj(f, target_s3_bucket, fileObj )
                        show_val("Uploaded", fileObj)

    except Exception as e:
            print("Error %s" %e)
            raise click.Abort()

## COLLECT RELEASE
#
@cli.command("collect-release")
@click.pass_obj
@click.argument("target-path", type=click.Path(exists=False, writable=True), default="artifacts/chain-1")
@click.option(
    "-n",
    "--network-name",
    help="The network name (also set in chainspec), defaults to output directory name",
)
@click.option(
    "--get-from-url",
    type=STRING,
    default="http://genesis.casperlabs.io/casper",
    help="Release Builds Url (default=mainnet)",
)
@click.option(
    "--node-version",
    type=STRING,
    default="1_0_0",
    help="Release Node Version (default=1_0_0)",
)
# collect release
def collect_release(
    obj,
    target_path,
    network_name,
    get_from_url,
    node_version
):

    if not network_name:
        network_name = os.path.basename(os.path.join(target_path))

    source_packages_path = os.path.join(target_path, "source")

    protocol_source_packages_path = os.path.join(source_packages_path, "1_0_0")
    protocol_source_packages_download_path = os.path.join(source_packages_path, "1_0_0", "download")

    Path(protocol_source_packages_download_path).mkdir(parents=True, exist_ok=True)

    try:
        # get released packages from url (http)
        if ( get_from_url and node_version ):

            show_val("Sourcing Build from", "{}/{}".format(get_from_url, node_version))
            
            for file in ['config.tar.gz','bin.tar.gz']: 

                url = os.path.join(get_from_url,node_version,file)
                connection = requests.get(url, allow_redirects=True, timeout=3)

                if connection.status_code == 200:
                    open(os.path.join(protocol_source_packages_download_path, file), 'wb').write(connection.content)

                f = open(os.path.join(protocol_source_packages_download_path, file), 'rb')
                tar = tarfile.open(fileobj=f, mode='r:gz')
                tar.extractall(path=protocol_source_packages_path)

            show_val("Source Build Artifacts in", "{}/{}".format(source_packages_path, node_version))

    except Exception as e:
        print("Error %s" %e)
        raise click.Abort()

    

## CREATE NETWORK ARTIFACTS
#
@cli.command("create-network")
@click.pass_obj
@click.argument("target-path", type=click.Path(exists=False, writable=True), default="artifacts/chain-1")
@click.option(
    "-k",
    "--hosts-file",
    help="Parse an hosts.yaml file, using all.children.validators for set of known nodes",
    default=None
)
@click.option(
    "-n",
    "--network-name",
    help="The network name (also set in chainspec), defaults to output directory name",
)
@click.option(
    "-g",
    "--genesis-in",
    help="Number of seconds from now until Genesis",
    default=300,
    type=int,
)
@click.option(
    "-v",
    "--node-version",
    type=str,
    help="semver with underscores e.g. 1_0_0",
    default="1_0_0"
)
@click.option(
    "--source-config",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Node configuration template to source from",
)
@click.option(
    "--source-chainspec",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Chainspec template to source from",
)
@click.option(
    "--source-casper-node",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Casper node binary to source from",
)
# create network
def create_network(
    obj,
    target_path,
    hosts_file,
    network_name,
    genesis_in,
    node_version,
    source_chainspec,
    source_config,
    source_casper_node
):
    
    if not network_name:
        network_name = os.path.basename(os.path.join(target_path))

    node_version = "1_0_0" 
    # Create the network output directories.
    show_val("Output path", target_path)

    nodes_path = \
        os.path.join(target_path, "nodes")
    sources_path = os.path.join(target_path, "source")
    staging_path = os.path.join(target_path, "staging")
    target_path = os.path.join(target_path, "target")

    sources_version_path = \
        os.path.join(sources_path, node_version)
    target_version_path = \
        os.path.join(target_path, node_version)

    bin_path = \
        os.path.join(staging_path, "bin")
    bin_version_path = \
        os.path.join(staging_path, "bin", node_version)
    config_path = \
        os.path.join(staging_path, "config")
    config_version_path = \
        os.path.join(config_path, node_version)

    # Staging directories for config, chain
    show_val("Node version", node_version)

    show_val("Node Count", obj["validator-node-count"] + obj["zero-weight-node-count"])
    
    try:
        Path(nodes_path).mkdir(parents=True)
        Path(bin_path).mkdir(parents=True)
        Path(bin_version_path).mkdir(parents=True)
        Path(config_path).mkdir(parents=True)
        Path(target_version_path).mkdir(parents=True)
        Path(config_version_path).mkdir(parents=True)

        if source_chainspec:
            chainspec_template = source_chainspec
        elif os.path.isfile(os.path.join(sources_version_path, 'chainspec.toml')):
            chainspec_template = os.path.join(sources_version_path, 'chainspec.toml')
        else:
            raise Exception("no chainspec_template found")

        if source_config:
            config_template = source_config
        elif os.path.isfile(os.path.join(sources_version_path, 'config-example.toml')):
            config_template = os.path.join(sources_version_path, 'config-example.toml')
        else:
            raise Exception("no config_template found")

        if source_casper_node:
            casper_node_bin = source_casper_node
        elif os.path.isfile(os.path.join(sources_version_path, 'casper-node')):
            casper_node_bin = os.path.join(sources_version_path, 'casper-node')
        else:
            raise Exception("no casper_node_bin found")

        # Update chainspec values.
        chainspec = create_chainspec(
            chainspec_template, network_name, genesis_in
        )

        # Dump chainspec into staging dir
        chainspec_path = os.path.join(config_version_path, "chainspec.toml")
        toml.dump(chainspec, open(chainspec_path, "w"))
        show_val("Chainspec", chainspec_path)

        # Copy casper-node into bin/VERSION/ staging dir
        node_bin_path = os.path.join(bin_version_path, "casper-node")
        shutil.copyfile(casper_node_bin, node_bin_path)
        os.chmod(node_bin_path, 0o744)

        if hosts_file:
            # Load validators from ansible yaml inventory
            hosts = yaml.load(open(hosts_file), Loader=yaml.FullLoader)
        else:
            hosts = create_hosts_file(network_name, obj)


        # Setup each node, collecting all pubkey hashes.
        show_val("Node config template", config_template)

        validator_nodes = list(hosts["all"]["children"]
                            ["validators"]["hosts"].keys())
        bootstrap_nodes = list(hosts["all"]["children"]
                            ["bootstrap"]["hosts"].keys())
        zero_weight_nodes = list(
            hosts["all"]["children"]["zero_weight"]["hosts"].keys())

        bootstrap_keys = list()
        validator_keys = list()
        zero_weight_keys = list()

        for public_address in bootstrap_nodes:
            show_val("bootstrap node", public_address)
            key_path = os.path.join(
                nodes_path, public_address, "etc", "casper", "keys")
            account = generate_account_key(key_path, public_address, obj)
            generate_node_config(bootstrap_nodes, config_template, obj, nodes_path,
                        node_version, public_address, None)
            validator_keys.append(account)

        initial_known_nodes = bootstrap_nodes

        for public_address in validator_nodes:
            show_val("validator node", public_address)
            key_path = os.path.join(
                nodes_path, public_address, "etc", "casper", "keys")
            account = generate_account_key(key_path, public_address, obj)
            generate_node_config(
                initial_known_nodes + validator_nodes, config_template,
                obj, nodes_path, node_version, public_address, None)
            validator_keys.append(account)

        for public_address in zero_weight_nodes:
            show_val("zero weight node", public_address)
            key_path = os.path.join(
                nodes_path, public_address, "etc", "casper", "keys")
            account = generate_account_key(key_path, public_address, obj)
            generate_node_config(
                initial_known_nodes + validator_nodes, config_template,
                obj, nodes_path, node_version, public_address, None)
            zero_weight_keys.append(account)

        # config-example.toml
        generate_example_node_config(
                initial_known_nodes + validator_nodes, config_template,
                obj, config_version_path, node_version, "<EXAMPLE>", None)

        faucet_path = os.path.join(staging_path, "faucet")
        faucet_key = generate_account_key(faucet_path, "faucet", obj)

        accounts_path = os.path.join(config_version_path, "accounts.toml")

        # Copy accounts.toml into staging dir
        create_accounts_toml(accounts_path, faucet_key,
                            bootstrap_keys + validator_keys, zero_weight_keys)

        for public_address in bootstrap_nodes + validator_nodes + zero_weight_nodes:
            node_path = os.path.join(nodes_path, public_address)
            show_val("copying files to ", node_path)

            # copy the bin and chain into each node's versioned fileset
            node_var_lib_casper = os.path.join(node_path, "var", "lib", "casper")
            Path(node_var_lib_casper).mkdir(parents=True)

            # should already exist
            node_config_path = \
                os.path.join(node_path, "etc", "casper", node_version)

            node_key_path = os.path.join(node_path, "etc", "casper", "keys")

            # copy the faucet's secret_key.pem into each node's config
            faucet_target_path = os.path.join(node_key_path, "faucet")
            Path(faucet_target_path).mkdir(parents=True)
            shutil.copyfile(
                os.path.join(faucet_path, "secret_key.pem"),
                os.path.join(faucet_target_path, "secret_key.pem")
            )

            for filename in os.listdir(config_version_path):
                shutil.copyfile(
                    os.path.join(config_version_path, filename),
                    os.path.join(node_config_path, filename)
                )

        # Create config.tar.gz and bin.tar.gz for publishing
        create_protocol_package(network_name, obj, bin_version_path, config_version_path, target_path, node_version)

    except Exception as e:
        print("Error %s" %e)
        raise click.Abort()


# get account Public key HEX
def generate_account_key(key_path, public_address, obj):
    run_client(obj["casper_client_argv0"], "keygen", key_path)
    pubkey_hex = open(os.path.join(key_path, "public_key_hex")).read().strip()
    return pubkey_hex

# create config.toml
def generate_node_config(known_addresses, config_template, obj, nodes_path, node_version, public_address, trusted_hash):
    node_path = os.path.join(nodes_path, public_address)
    node_config_path = \
        os.path.join(node_path, "etc", "casper", node_version)
    Path(node_config_path).mkdir(parents=True, exist_ok=True)
    config = toml.load(open(config_template))

    if trusted_hash:
        config["node"]["trusted_hash"] = trusted_hash

    config["consensus"]["secret_key_path"] = os.path.join(
        "..", "keys", "secret_key.pem")
    # add faucet to the `faucet` subfolder in keys
    config["logging"]["format"] = "text"
    config["network"]["public_address"] = "{}:{}".format(
        public_address, obj["casper-node-port"])
    config["network"]["bind_address"] = "0.0.0.0:{}".format(obj["casper-node-port"])
    config["network"]["known_addresses"] = [
        "{}:{}".format(n, obj["casper-node-port"]) for n in known_addresses]
    # Setup for volume operation.
    storage_path = "/storage/{}".format(public_address)
    config["storage"]["path"] = storage_path

    try:
        config["consensus"]["highway"]["unit_hashes_folder"] = storage_path
    except KeyError:
        config["consensus"]["unit_hashes_folder"] = storage_path

    toml.dump(config, open(os.path.join(node_config_path, "config.toml", ), "w"))

# create config-example.toml
def generate_example_node_config(known_addresses, config_template, obj, nodes_path, node_version, public_address, trusted_hash):
    node_config_path = nodes_path
    Path(node_config_path).mkdir(parents=True, exist_ok=True)
    config = toml.load(open(config_template))

    if trusted_hash:
        config["node"]["trusted_hash"] = trusted_hash

    config["consensus"]["secret_key_path"] = os.path.join(
        "..", "keys", "secret_key.pem")
    # add faucet to the `faucet` subfolder in keys
    config["logging"]["format"] = "text"
    config["network"]["public_address"] = "{}:{}".format(
        public_address, obj["casper-node-port"])
    config["network"]["bind_address"] = "0.0.0.0:{}".format(obj["casper-node-port"])
    config["network"]["known_addresses"] = [
        "{}:{}".format(n, obj["casper-node-port"]) for n in known_addresses]
    # Setup for volume operation.
    storage_path = "/storage/{}".format(public_address)
    config["storage"]["path"] = storage_path
    config["network"]["gossip_interval"] = 120000
    try:
        config["consensus"]["highway"]["unit_hashes_folder"] = storage_path
    except KeyError:
        config["consensus"]["unit_hashes_folder"] = storage_path
        
    toml.dump(config, open(os.path.join(node_config_path, "config-example.toml", ), "w"))

# create chainspec.toml
def create_chainspec(template, network_name, genesis_in):
    """Creates a new chainspec from a template.
    `contract_path` must be a dictionary mapping the keys of `CONTRACTS` to relative or absolute
    paths to be put into the new chainspec.
    Returns a dictionary that can be serialized using `toml`.
    """
    show_val("Chainspec template", template)
    chainspec = toml.load(open(template))

    show_val("Chain name", network_name)
    genesis_timestamp = (datetime.utcnow() + timedelta(seconds=genesis_in)).isoformat(
        "T"
    ) + "Z"
    show_val("Genesis timestamp", "{} (in {} seconds)".format(
        genesis_timestamp, genesis_in))
    chainspec["network"]["name"] = network_name
    chainspec["protocol"]["activation_point"] = genesis_timestamp

    chainspec["core"]["unbonding_delay"] = 7 # normally 14
    chainspec["core"]["auction_delay"] = 1 # normally 3
    chainspec["core"]["era_duration"] = "15min" # normally 30min
    chainspec["deploys"]["block_max_transfer_count"] = 500
    chainspec["protocol"]["version"] = '1.0.0'
    return chainspec


def create_accounts_toml(accounts_path, faucet, validators, zero_weight_ops):
    """
    :param output_file: accounts.toml
    :param faucet: public key of faucet account
    :param validators: public keys of validators with weight
    :param zero_weight_ops: public keys of zero weight operators
    :return: output_file will be an appropriately formatted csv
    """
    accounts = {"accounts": [
        {
            "public_key": faucet,
            "balance": str(10**32),
            "bonded_amount": str(0),
        }
    ], "delegators": []}

    for index, key_hex in enumerate(validators):
        motes = 10**32
        staking_weight = 10**13 + index
        account = {
            "public_key": key_hex,
            "balance": str(motes),
            "validator" : { "bonded_amount": str(staking_weight) },
        }
        accounts["accounts"].append(account)

    for key_hex in zero_weight_ops:
        motes = 10**32
        staking_weight = 0
        account = {
            "public_key": key_hex,
            "balance": str(motes),
            "bonded_amount": str(staking_weight),
        }
        accounts["accounts"].append(account)

    toml.dump(accounts, open(accounts_path, "w"))

def create_hosts_file(network_name, obj):

    validator_count = obj["validator-node-count"]
    zero_weight_count = obj["zero-weight-node-count"]
    total_node_count = validator_count + zero_weight_count
    #show_val("Total Node Count", total_node_count)

    # default hosts count list
    hosts_file = {
        "all": {
            "children": {
                "bootstrap": {
                    "hosts": {}
                },
                "validators": {
                    "hosts": {}
                },
                "zero_weight": {
                    "hosts": {}
                }
            }
        }
    }

    for node_index in range(1,2):
        hosts_file["all"]["children"]["bootstrap"]["hosts"].update({ "{}-{}".format("casper-node", str(node_index).zfill(3)): ""})
    for node_index in range(2, total_node_count - zero_weight_count + 1):
        hosts_file["all"]["children"]["validators"]["hosts"].update({ "{}-{}".format("casper-node", str(node_index).zfill(3)): ""})
    for node_index in range(validator_count + 1, total_node_count + 1):
        hosts_file["all"]["children"]["zero_weight"]["hosts"].update({ "{}-{}".format("casper-node", str(node_index).zfill(3)): ""})

    return(hosts_file)

def create_protocol_package(network_name, obj, staging_bin_path, staging_config_path, target_path, node_version):
    
    current_path = os.path.dirname(os.path.abspath(__file__))
    staging_bin_full_path = os.path.join(current_path, staging_bin_path)

    # write protocol_versions file in target_path
    protocol_file_path = os.path.join(current_path, target_path, 'protocol_versions')
    with open(protocol_file_path, 'w+') as f:
        f.write(node_version)
    show_val("Protocol_versions file", os.path.join(current_path, target_path, 'protocol_versions'))

    # create bin.tar.gz in target_path/node_version
    tar_path = os.path.join(current_path, target_path, node_version)
    os.chdir(staging_bin_full_path)
    with tarfile.open(os.path.join(tar_path,'bin.tar.gz'), "w:gz") as tar:
        for file in ["casper-node"]:
            tar.add(os.path.basename(file))
    show_val("Binary archive", os.path.join(tar_path,'bin.tar.gz'))

    # create config.tar.gz in target_path/node_version
    staging_config_full_path = os.path.join(current_path, staging_config_path)
    tar_path = os.path.join(current_path, target_path, node_version)
    os.chdir(staging_config_full_path)
    with tarfile.open(os.path.join(tar_path, 'config.tar.gz'), "w:gz") as tar:
        for file in ["chainspec.toml","config-example.toml","accounts.toml"]:
            tar.add(os.path.basename(file))
    show_val("Config archive", os.path.join(tar_path, 'config.tar.gz'))

    os.chdir(current_path)

def run_client(argv0, *args):
    """Run the casper client, compiling it if necessary, with the given command-line args"""
    return subprocess.check_output(argv0 + list(args))


def show_val(key, value):
    """Auxiliary function to display a value on the terminal."""

    key = "{:>20s}".format(key)
    click.echo("{}:  {}".format(click.style(key, fg="blue"), value))


if __name__ == "__main__":
    cli()
