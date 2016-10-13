# Intro

The `dwm` package is a standalone set of business logic for maintaining marketing database quality. This repo is an Openshift-based implementation which applies said package to an Eloqua instance.

# Architecture

## Data flow

![alt text](/diagrams/DWMOps_SystemFlow.png "High-level flow of using the DWM")

The data flow of this app uses a queue-based processing system (using the package `pyqm`):

### Hourly scripts:
1. *Eloqua_Contacts_GetDWM.py*
  - Export the specified contacts from Eloqua via Bulk API (using Python package `pyeloqua`)
  - Add them to the queue `dwmQueue`
2. *Eloqua_Contacts_PostDWM.py*
  - Pick up records that have finished processing and import back to Eloqua
  - limit 30k to avoid data limits
  - References queue `processedQueue`
  - Removes from shared list on import

### Minutely scripts:
1. *Eloqua_Contacts_RunDWM.py*
  - Run the `dwmAll` function on a set of contacts
  - 600, currently
  - when done, remove from `dwmQueue` and add to `processedQueue`
2. *Eloqua_Contacts_CleanQueues.py*
  - Run a queue cleanup script
  - Timeout records with locks older than 300 seconds
  - Report current queue size and timeout stats to Prometheus for monitoring

This system provides enough redundancy to allow for troubleshooting of a crashed script. Also helps minimize the impact on Bulk API utilization limits.

## Custom functions

Current implementation has two custom functions:
- `CleanZipcodeUS`
  - Apply zipcode standardization to contacts where `country='US'`
  - Takes only first string of numbers before a non-digit character
  - Strips down to first 5 digits
  - Adds leading 0s which may have been stripped by Excel auto-formatting
- `CleanAnnualRevenue`
  - Remove any "," or "$" characters
  - Try converting to integer
    - If successful, group into pre-determined `annualRevenue` bucket

## Logging

### Eloqua_Contacts_CleanQueues.py
- Logfile: `$OPENSHIFT_LOG_DIR/CLEAN_QUEUE_DWM_YYYY_MM_DD.log`
  - Explicitly logged runtime info
  - Accounted for exceptions
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts_CleanQueues_Console_YYYY_MM_DD.log`
  - Runtime console output (including uncaught exceptions)
- Prometheus metrics (SLI):
  - *QueueSize*: # of records currently in each queue
  - *QueueTimeout*: # of records "released" back into queue after timeout
  - *last_success_unixtime*: Last time of successful run

### Eloqua_Contacts_GetDWM.py
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts_DWM_GET_YYYY_MM_DD.log `
  - Explicitly logged runtime info
  - Accounted for exceptions
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts_GetDWM_Console_YYYY_MM_DD.log`
  - Runtime console output (including uncaught exceptions)
- Prometheus metrics (SLI):
  - *last_success_unixtime*: Last time of successful run
  - *total_seconds*: # of seconds to complete entire script
  - *total_records_total*: # of records processed

### Eloqua_Contacts_RunDWM.py
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts_DWM_RUN_YYYY_MM_DD.log`
  - Explicitly logged runtime info
  - Accounted for exceptions
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts_RunDWM_Console_YYYY_MM_DD.log`
  - Runtime console output (including uncaught exceptions)
  - If argument `verbose=True`, includes `tqdm` output 'progress bar', showing # records / second
- Prometheus metrics (SLI):
  - *last_success_unixtime*: Last time of successful run
  - *total_seconds*: # of seconds to complete entire script
  - *total_records_total*: # of records processed
  - *total_seconds_dwm*: # of seconds to complete DWM functions (not including queue processing time)

### Eloqua_Contacts_PostDWM.py
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts_DWM_POST_YYYY_MM_DD.log`
  - Explicitly logged runtime info
  - Accounted for exceptions
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts_PostDWM_Console_YYYY_MM_DD.log`
  - Runtime console output (including uncaught exceptions)
- Prometheus metrics (SLI):
  - *last_success_unixtime*: Last time of successful run
  - *total_seconds*: # of seconds to complete entire script
  - *total_records_total*: # of records processed
  - *total_records_errored*: # of records from batches which received an an error on import
  - *total_records_warning*: # of records from batches which received a warning on import
  - *total_records_success*: # of records which successfully imported to Eloqua

# Setup

## Gears

This implementation use ITOS (Red Hat IT-Hosted Openshift v2; comparable to Openshift Enterprise). Using the Openshift PaaS is, in this case, not the best use of it's capabilities as this implementation has no API capabilities, nor any other need to have running web services. But, it is a good rapid deployment solution in that it's fast and consistent in setup.

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

### Cron

# TODO
- Build an API operating off the same MongoDB
