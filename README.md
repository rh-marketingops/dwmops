# Intro

# Architecture

# Troubleshooting

# Setup

## Gears

### Python

- Internal-hosted medium gear
- Python 3.3
- Scalable; set to 1
- 1GB storage

#### Environment Variables

- Eloqua variables (service account)
  - `ELOQUA_COMPANY`
  - `ELOQUA_USERNAME`
  - `ELOQUA_PASSWORD`
- Monitoring
  - `PUSHGATEWAY` (for Prometheus monitoring of batch jobs)

### MongoDB

- Internal-hosted medium gear
- MongoDB 3.2
  - https://github.com/icflorescu/openshift-cartridge-mongodb
- 10GB storage
