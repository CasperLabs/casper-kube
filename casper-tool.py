#!/usr/bin/env python3

from datetime import datetime, timedelta
import os
import subprocess

import click
import shutil
import toml
import yaml
import tarfile
from pathlib import Path
from itertools import chain

#: The port the node is reachable on.
NODE_PORT = 34553


@click.group()
@click.option(
    "-b",
    "--basedir",
    help="casper-node source code base directory",
    type=click.Path(exists=True, dir_okay=True,
                    file_okay=False, readable=True),
    default=os.path.join(os.path.dirname(__file__), "..", "casper-node"),
)
@click.option(
    "-l",
    "--launcher",
    help="casper-node-launcher source code base directory",
    type=click.Path(exists=True, dir_okay=True,
                    file_okay=False, readable=True),
    default=os.path.join(os.path.dirname(__file__),
                         "..", "casper-node-launcher"),
)
@click.option(
    "--casper-client",
    help="path to casper client binary (compiled from basedir by default)",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    default="../casper-node/target/release/casper-client",
)
@click.option(
    "-p",
    "--production",
    is_flag=True,
    help="Use production chainspec template instead of dev/local",
)
@click.option(
    "-c",
    "--config-template",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Node configuration template to use",
)
@click.option(
    "-C",
    "--chainspec-template",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Chainspec template to use",
)
@click.pass_context
def cli(
    ctx,
    basedir,
    launcher,
    production,
    chainspec_template,
    config_template,
    casper_client,
):
    """Casper Network creation tool

    Can be used to create new casper-labs chains with automatic validator setups. Useful for testing."""
    obj = {}
    if chainspec_template:
        obj["chainspec_template"] = chainspec_template
    else:
        obj["chainspec_template"] = os.path.join(
            basedir, "resources", "production", "chainspec.toml"
        )
        show_val("using production chainspec", obj["chainspec_template"])

    if config_template:
        obj["config_template"] = chainspec_template
    elif production:
        obj["config_template"] = os.path.join(
            basedir, "resources", "production", "config.toml"
        )
    else:
        obj["config_template"] = os.path.join(
            basedir, "resources", "local", "config.toml"
        )

    if casper_client:
        obj["casper_client_argv0"] = [casper_client]
    else:
        obj["casper_client_argv0"] = [
            "cargo",
            "run",
            "--quiet",
            "--manifest-path={}".format(os.path.join(basedir,
                                                     "client", "Cargo.toml")),
            "--",
        ]

    obj["casper-node-bin"] = \
        os.path.join(basedir, "target", "release", "casper-node")
    obj["casper-node-launcher-bin"] = \
        os.path.join(launcher, "target", "release", "casper-node-launcher")

    ctx.obj = obj
    return


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
    shutil.copyfile(obj["casper-node-bin"], node_bin_path)
    os.chmod(node_bin_path, 0o744)

    # Copy casper-node-launcher into bin/ staging dir
    launcher_bin_path = os.path.join(bin_path, "casper-node-launcher")
    shutil.copyfile(obj["casper-node-launcher-bin"], launcher_bin_path)
    os.chmod(launcher_bin_path, 0o744)

    show_val("Creating binary archive", "bin.tar.bz2")
    with tarfile.open(os.path.join(staging_path, "bin.tar.bz2"), "w:bz2") as tar:
        tar.add(bin_path, arcname=os.path.basename(bin_path))

    faucet_path = os.path.join(staging_path, "faucet")

    # Load validators from ansible yaml inventory
    hosts = yaml.load(open(hosts_file), Loader=yaml.FullLoader)
    show_val("Node config template", obj["config_template"])

    joining_nodes = list(hosts["all"]["children"]["joiners"]["hosts"].keys())
    validator_nodes = list(hosts["all"]["children"]
                           ["validators"]["hosts"].keys())
    bootstrap_nodes = list(hosts["all"]["children"]
                           ["bootstrap"]["hosts"].keys())

    for public_address in joining_nodes:
        show_val("adding joining node", public_address)
        generate_node(validator_nodes + bootstrap_nodes, obj,
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


@cli.command("create-network")
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
def create_network(
    obj,
    target_path,
    hosts_file,
    network_name,
    genesis_in,
    node_version,
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

    Path(nodes_path).mkdir(parents=True)
    Path(bin_path).mkdir(parents=True)
    Path(bin_version_path).mkdir(parents=True)
    Path(config_path).mkdir(parents=True)

    # Update chainspec values.
    chainspec = create_chainspec(
        obj["chainspec_template"], network_name, genesis_in
    )

    # Dump chainspec into staging dir
    chainspec_path = os.path.join(config_path, "chainspec.toml")
    toml.dump(chainspec, open(chainspec_path, "w"))
    show_val("Chainspec", chainspec_path)

    # Copy casper-node into bin/VERSION/ staging dir
    node_bin_path = os.path.join(bin_version_path, "casper-node")
    shutil.copyfile(obj["casper-node-bin"], node_bin_path)
    os.chmod(node_bin_path, 0o744)

    # Copy casper-node-launcher into bin/ staging dir
    launcher_bin_path = os.path.join(bin_path, "casper-node-launcher")
    shutil.copyfile(obj["casper-node-launcher-bin"], launcher_bin_path)
    os.chmod(launcher_bin_path, 0o744)

    # Copy casper-client into bin/ staging dir
    client_bin_path = os.path.join(bin_path, "casper-client")
    show_val("copying client", obj["casper_client_argv0"][0])
    shutil.copyfile(obj["casper_client_argv0"][0], client_bin_path)
    os.chmod(client_bin_path, 0o744)

    bin_archive_path = os.path.join(staging_path, "bin.tar.bz2")
    if Path("/home/ubuntu/bin.tar.bz2").exists():
        show_val("Found existing binary archive", "/home/ubuntu/bin.tar.bz2")
        shutil.copyfile("/home/ubuntu/bin.tar.bz2", bin_archive_path)
    else:
        show_val("Creating binary archive", "bin.tar.bz2")
        with tarfile.open(bin_archive_path, "w:bz2") as tar:
            tar.add(bin_path, arcname=os.path.basename(bin_path))

    # Load validators from ansible yaml inventory
    hosts = yaml.load(open(hosts_file), Loader=yaml.FullLoader)

    # Setup each node, collecting all pubkey hashes.
    show_val("Node config template", obj["config_template"])

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
        generate_node(bootstrap_nodes, obj, nodes_path,
                      node_version, public_address, None)
        validator_keys.append(account)

    initial_known_nodes = bootstrap_nodes  # + validator_nodes

    for public_address in validator_nodes:
        show_val("validator node", public_address)
        key_path = os.path.join(
            nodes_path, public_address, "etc", "casper", "keys")
        account = generate_account_key(key_path, public_address, obj)
        generate_node(
            initial_known_nodes,
            obj, nodes_path, node_version, public_address, None)
        validator_keys.append(account)

    for public_address in zero_weight_nodes:
        show_val("zero weight node", public_address)
        key_path = os.path.join(
            nodes_path, public_address, "etc", "casper", "keys")
        account = generate_account_key(key_path, public_address, obj)
        generate_node(
            initial_known_nodes,
            obj, nodes_path, node_version, public_address, None)
        zero_weight_keys.append(account)

    faucet_path = os.path.join(staging_path, "faucet")
    faucet_key = generate_account_key(faucet_path, "faucet", obj)

    accounts_path = os.path.join(config_path, "accounts.toml")
    # Copy accounts.toml into staging dir
    create_accounts_toml(accounts_path, faucet_key,
                         bootstrap_keys + validator_keys, zero_weight_keys)

    for public_address in bootstrap_nodes + validator_nodes + zero_weight_nodes:
        node_path = os.path.join(nodes_path, public_address)
        show_val("coping files to ", node_path)

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

        for filename in os.listdir(config_path):
            shutil.copyfile(
                os.path.join(config_path, filename),
                os.path.join(node_config_path, filename)
            )


def generate_account_key(key_path, public_address, obj):
    run_client(obj["casper_client_argv0"], "keygen", key_path)
    pubkey_hex = open(os.path.join(key_path, "public_key_hex")).read().strip()
    return pubkey_hex


def generate_node(known_addresses, obj, nodes_path, node_version, public_address, trusted_hash):
    node_path = os.path.join(nodes_path, public_address)
    node_config_path = \
        os.path.join(node_path, "etc", "casper", node_version)
    Path(node_config_path).mkdir(parents=True, exist_ok=True)
    config = toml.load(open(obj["config_template"]))

    if trusted_hash:
        config["node"]["trusted_hash"] = trusted_hash

    config["consensus"]["secret_key_path"] = os.path.join(
        "..", "keys", "secret_key.pem")
    # add faucet to the `faucet` subfolder in keys
    config["logging"]["format"] = "json"
    config["network"]["public_address"] = "{}:{}".format(
        public_address, NODE_PORT)
    config["network"]["bind_address"] = "0.0.0.0:{}".format(NODE_PORT)
    config["network"]["known_addresses"] = [
        "{}:{}".format(n, NODE_PORT) for n in known_addresses]
    # Setup for volume operation.
    storage_path = "/storage/{}".format(public_address)
    config["storage"]["path"] = storage_path
    config["storage"]["path"] = storage_path
    config["network"]["gossip_interval"] = 120000
    config["consensus"]["unit_hashes_folder"] = storage_path
    toml.dump(config, open(os.path.join(node_config_path, "config.toml", ), "w"))


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
    chainspec["network"]["timestamp"] = genesis_timestamp
    chainspec["highway"]["minimum_round_exponent"] = 13
    chainspec["highway"]["maximum_round_exponent"] = 16
    chainspec["core"]["unbonding_delay"] = 7 # normally 14
    chainspec["core"]["auction_delay"] = 1 # normally 3
    chainspec["core"]["era_duration"] = "15min" # normally 30min
    chainspec["deploys"]["block_max_transfer_count"] = 500
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


def run_client(argv0, *args):
    """Run the casper client, compiling it if necessary, with the given command-line args"""
    return subprocess.check_output(argv0 + list(args))


def show_val(key, value):
    """Auxiliary function to display a value on the terminal."""

    key = "{:>20s}".format(key)
    click.echo("{}:  {}".format(click.style(key, fg="blue"), value))


if __name__ == "__main__":
    cli()
