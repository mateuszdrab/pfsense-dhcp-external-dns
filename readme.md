# Pfsense DHCP to External DNS CRD

A Python script designed to generate an ExternalDNS DNSEndpoint resource from DHCP leases on a pfSense firewall. It processes DHCP leases and produces DNS A, PTR, and TXT endpoints for ExternalDNS to apply.

## Requirements

- Python 3.x
- `pypfsense` library
- `PyYAML` library

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
sites:
  "10": "site1"
  "20": "site2"
pfsense:
  url: "https://your_pfsense_url"
  username: "your_pfsense_username"
  password: "your_pfsense_password"
  verify_ssl: false # Set to true if you want to verify the SSL certificate
```

## Sites Mapping

The code includes functionality to map different sites, which can be useful when one DHCP server is serving multiple sites or locations. The sites are mapped based on the third octet of the IP address, allowing for easy identification and handling of IP addresses based on their site or location.

## Records example

For a lease with name example-lease and IP address 192.23.45.67 and the domain example.com, the following endpoints will be created:

- A record: example-lease.example.com with the IP address 192.23.45.67
- TXT record: example-lease.example.com with the MAC address of the lease
- PTR record: a PTR record for 67 in the 45.23.192.in-addr.arpa zone pointing to example-lease.example.com

## Usage

Run the script with the configuration file as an argument:

```sh
python app/app.py config.yaml
```

If no configuration file is provided, the script will default to `config.yaml`.

## Output

The script outputs a single DNSEndpoint resource in YAML format, ready to be applied to your cluster for ExternalDNS to consume.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

Includes `pypfsense` module from the repository [travisghansen/hass-pfsense](https://github.com/travisghansen/hass-pfsense)
