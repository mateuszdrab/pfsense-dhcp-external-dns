import pypfsense
import yaml
import sys
import argparse
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException
from datetime import datetime

# Parse command line arguments
parser = argparse.ArgumentParser(
    description="Generate or apply DNSEndpoint from pfSense DHCP leases"
)
parser.add_argument(
    "config_file", nargs="?", default="config.yaml", help="Path to config.yaml file"
)
parser.add_argument(
    "--apply", action="store_true", help="Apply the DNSEndpoint to the cluster"
)
args = parser.parse_args()

_config_path = args.config_file
_should_apply = args.apply

# Load configuration from YAML file
with open(_config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

_subnets = config.get("subnets", {})
_zone = config["zone"]
_pfsense_config = config["pfsense"]
_dnsendpoint_name = config.get("dnsendpoint_name", "pfsense-dhcp-leases")
_dnsendpoint_namespace = config.get("dnsendpoint_namespace")
_default_ttl = config.get("ttl", 300)
_create_ptr_records = config.get("create_ptr_records", False)


def build_endpoints_for_lease(lease):
    # Configuration
    ip = lease["ip"]
    octet = ip.split(".")[2]
    record_name_a = (
        lease["hostname"] + "." + _subnets[octet]
        if octet in _subnets
        else lease["hostname"]
    )
    record_name_ptr = lease["ip"].split(".")[3]
    fqdn_a = record_name_a + "." + _zone
    ptr_zone = octet + ".168.192.in-addr.arpa"
    ptr_dns_name = record_name_ptr + "." + ptr_zone

    endpoints_list = [
        {
            "dnsName": fqdn_a,
            "recordType": "A",
            "targets": [ip],
            "recordTTL": _default_ttl,
        },
        {
            "dnsName": fqdn_a,
            "recordType": "TXT",
            "targets": [lease["mac"]],
            "recordTTL": _default_ttl,
        },
    ]
    if _create_ptr_records:
        endpoints_list.append(
            {
                "dnsName": ptr_dns_name,
                "recordType": "PTR",
                "targets": [fqdn_a],
                "recordTTL": _default_ttl,
            }
        )
    return endpoints_list


# Create a connection to the pfSense firewall
pfsense = pypfsense.Client(
    _pfsense_config["url"],
    _pfsense_config["username"],
    _pfsense_config["password"],
    # Get the verify_ssl option from the config file
    opts=(
        {"verify_ssl": _pfsense_config["verify_ssl"]}
        if "verify_ssl" in _pfsense_config
        else {}
    ),
)

leases = pfsense.get_dhcp_leases()

# Filter leases with no hostname or empty hostname and 3rd octet in IP address is in _subnets
filtered_leases = [
    lease
    for lease in leases
    if lease["hostname"] and lease["hostname"] != ""
    # and lease["ip"].split(".")[2] in _subnets.keys()
]

endpoints = []

# Loop through filtered leases and collect endpoints
for lease in filtered_leases:
    endpoints.extend(build_endpoints_for_lease(lease))

dnsendpoint = {
    "apiVersion": "externaldns.k8s.io/v1alpha1",
    "kind": "DNSEndpoint",
    "metadata": {"name": _dnsendpoint_name},
    "spec": {"endpoints": endpoints},
}

if _dnsendpoint_namespace:
    dnsendpoint["metadata"]["namespace"] = _dnsendpoint_namespace

if _should_apply:
    # Load in-cluster config
    k8s_config.load_incluster_config()
    custom_api = client.CustomObjectsApi()

    namespace = _dnsendpoint_namespace or "default"
    group = "externaldns.k8s.io"
    version = "v1alpha1"
    plural = "dnsendpoints"

    try:
        # Try to update existing resource
        custom_api.patch_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=_dnsendpoint_name,
            body=dnsendpoint,
        )
        print(
            f"[{datetime.now().isoformat()}] DNSEndpoint '{_dnsendpoint_name}' updated in namespace '{namespace}'",
            file=sys.stderr,
        )
    except ApiException as e:
        if e.status == 404:
            # Create new resource if it doesn't exist
            custom_api.create_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                body=dnsendpoint,
            )
            print(
                f"[{datetime.now().isoformat()}] DNSEndpoint '{_dnsendpoint_name}' created in namespace '{namespace}'",
                file=sys.stderr,
            )
        else:
            print(
                f"[{datetime.now().isoformat()}] Error applying DNSEndpoint: {e}",
                file=sys.stderr,
            )
            sys.exit(1)
else:
    # Print YAML to stdout
    print(yaml.safe_dump(dnsendpoint, sort_keys=False))
