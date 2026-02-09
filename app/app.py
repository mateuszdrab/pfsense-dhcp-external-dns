import pypfsense
import yaml
import sys

# Get config file path from YAML file from args if provided

if len(sys.argv) > 1:
    _config_path = sys.argv[1]
else:
    _config_path = "config.yaml"

# Load configuration from YAML file
with open(_config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

_sites = config["sites"]
_zone = config["zone"]
_pfsense_config = config["pfsense"]
_dnsendpoint_name = config.get("dnsendpoint_name", "pfsense-dhcp-leases")
_dnsendpoint_namespace = config.get("dnsendpoint_namespace")
_default_ttl = config.get("ttl", 300)


def build_endpoints_for_lease(lease):
    # Configuration
    ip = lease["ip"]
    octet = ip.split(".")[2]
    site = _sites[octet]
    record_name_a = lease["hostname"] + "." + site + ".cctv"
    record_name_ptr = lease["ip"].split(".")[3]
    fqdn_a = record_name_a + "." + _zone + "."
    ptr_zone = octet + ".168.192.in-addr.arpa"
    ptr_dns_name = record_name_ptr + "." + ptr_zone + "."

    return [
        {
            "dnsName": fqdn_a,
            "recordType": "A",
            "targets": [ip],
            "ttl": _default_ttl,
        },
        {
            "dnsName": fqdn_a,
            "recordType": "TXT",
            "targets": [lease["mac"]],
            "ttl": _default_ttl,
        },
        {
            "dnsName": ptr_dns_name,
            "recordType": "PTR",
            "targets": [fqdn_a],
            "ttl": _default_ttl,
        },
    ]


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

# Filter leases with no hostname or empty hostname and 3rd octet in IP address is in _sites
filtered_leases = [
    lease
    for lease in leases
    if lease["hostname"]
    and lease["hostname"] != ""
    and lease["ip"].split(".")[2] in _sites.keys()
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

print(yaml.safe_dump(dnsendpoint, sort_keys=False))
