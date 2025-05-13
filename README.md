> **WARNING** Logstory is a tool capable of transmitting logs and other data to
> security information and event management (SIEM) systems and/or other
> destinations for ingestion and storage. **It can be very difficult or
> impossible to remove data from these systems once they are ingested.**
> Ingesting data into your SIEM can have adverse effects on privacy, security,
> compliance, functionality, and more. You are responsible for the impact of
> ingesting data into your SIEM or other systems using Logstory. Please see the
> [Use cases](https://chronicle.github.io/logstory/#id1) section of the
> documentation for information regarding the Logstory datasets distributed with
> this repository.

> **NOTE** The *full* documentation for Logstory is at:
> https://chronicle.github.io/logstory/

# Logstory

Logstory is a utility for pre-processing and delivering security datasets to
[Google Security Operations (SecOps)](https://cloud.google.com/security/products/security-operations?hl=en).
Logstory addresses the complicated task of updating timestamps across a diverse
set of security log formats while maintaining the relative time differences
between events so that the dataset tells a repeatable story: a “Logstory.”
Logstory pre-processes datasets by modifying event timestamps and other elements
such as payload-embedded timestamps before delivering them to Google SecOps.
Logstory can also deliver datasets in specific sequences to ensure proper
enrichment in Google SecOps.

It is our hope that releasing Logstory as open-source software will help the
community test detection rules, develop SIEM content, create product
integrations (e.g., parsers and SOAR integrations), and assist with enabling
customer teams on how to best use Google SecOps. Logstory datasets typically
describe a discrete security scenario such as a simulated/emulated attack or a
particular MITRE ATT&CK technique or chain of techniques. Logstory datasets
can include raw security events (e.g. logs), entity data, detection rules, etc.

## Installation

Logstory is most easily installed from [The Python Package Index](https://pypi.org/).
Once installed, it offers a command line interface (CLI) which can be called
directly. See the [installation](https://chronicle.github.io/logstory/#installation)
section of the documentation for full details.

## Configuration

Configuration for Logstory is handled by command-line flags and/or stored
configuration files. Credentials used to authenticate to the SecOps instances
are also required. See the [configuration](https://chronicle.github.io/logstory/#configuration)
section of the documentation for full details.

## Usage

See the [use cases](https://chronicle.github.io/logstory/#configuration) section
in the full documentation for details.

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note
that this project is released with a Code of Conduct. By contributing to this
project, you agree to abide by its terms.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## License

Apache 2.0; see [`LICENSE`](LICENSE) for details.

## Disclaimer

Logstory is not an official Google project. It is not supported by
Google and Google specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.
