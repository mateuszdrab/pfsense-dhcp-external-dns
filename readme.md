# Pfsense DHCP to External DNS CRD

A Python script designed to generate an ExternalDNS DNSEndpoint resource from DHCP leases on a pfSense firewall. It processes DHCP leases and produces DNS A, PTR, and TXT endpoints for ExternalDNS to apply.

## Requirements

- Python 3.x
- `pypfsense` library
- `PyYAML` library
- `kubernetes` library (for `--apply` flag)

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/mateuszdrab/pfsense-dhcp-to-external-dns.git
    cd pfsense-dhcp-to-external-dns
    ```

2. Install the required Python libraries from the `requirements.txt` file:

    ```sh
    pip install -r requirements.txt
    ```

## Configuration

Create a `config.yaml` file in the root directory with the following structure:

```yaml
zone: "your_dns_zone"
dnsendpoint_name: "pfsense-dhcp-leases" # Optional
dnsendpoint_namespace: "external-dns" # Optional
ttl: 300 # Optional
subnets:
  "10": "subnet1"
  "20": "subnet2"
pfsense:
  url: "https://your_pfsense_url"
  username: "your_pfsense_username"
  password: "your_pfsense_password"
  verify_ssl: false # Set to true if you want to verify the SSL certificate
```

## Subnet Mapping

The code includes functionality to map different subnets, which can be useful when one DHCP server is serving multiple subnets or locations. The subnets are mapped based on the third octet of the IP address, allowing for easy identification and handling of IP addresses based on their subnet or location.

## Records example

For a lease with name example-lease and IP address 192.23.45.67 and the domain example.com, the following endpoints will be created:

- A record: example-lease.example.com with the IP address 192.23.45.67
- TXT record: example-lease.example.com with the MAC address of the lease
- PTR record: a PTR record for 67 in the 45.23.192.in-addr.arpa zone pointing to example-lease.example.com

## Usage

### Output YAML (default)

Run the script to output the DNSEndpoint resource as YAML:

```sh
python app/app.py config.yaml
```

If no configuration file is provided, the script will default to `config.yaml`.

You can pipe the output directly to kubectl:

```sh
python app/app.py config.yaml | kubectl apply -f -
```

### Apply to Cluster

When running as a pod in the cluster, use the `--apply` flag to apply the DNSEndpoint directly using the pod's service account:

```sh
python app/app.py config.yaml --apply
```

This requires the pod to be configured with a service account that has permissions to create/update DNSEndpoint resources in the target namespace.

## Output

The script outputs a single DNSEndpoint resource in YAML format (to stdout), ready to be applied to your cluster for ExternalDNS to consume.

When using the `--apply` flag, the script applies the DNSEndpoint directly to the cluster via the Kubernetes API and prints status messages to stderr.

## Deploying as a Kubernetes Pod

When deploying this as a pod in your cluster, ensure the pod's service account has the necessary RBAC permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pfsense-dhcp-external-dns-crd
rules:
- apiGroups: ["externaldns.k8s.io"]
  resources: ["dnsendpoints"]
  verbs: ["create", "update", "patch", "get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: pfsense-dhcp-external-dns-crd
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: pfsense-dhcp-external-dns-crd
subjects:
- kind: ServiceAccount
  name: pfsense-dhcp-external-dns
  namespace: default  # Change to your namespace
```

The pod will automatically use the mounted service account credentials when running with the `--apply` flag.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

Includes `pypfsense` module from the repository [travisghansen/hass-pfsense](https://github.com/travisghansen/hass-pfsense)
