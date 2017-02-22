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
  - when done, remove from `dwmQueue` and add to `indicatorQueue`
2. *Eloqua_Contacts_CleanQueues.py*
  - Run a queue cleanup script
  - Timeout records with locks older than 300 seconds
  - Report current queue size and timeout stats to Prometheus for monitoring
3. *Eloqua_Contacts_UpdateContactsIndicators.py*
  - Retrieve job from `indicatorQueue`
  - Update record in Contacts.Indicators (by `emailAddress`) and set `Contacts.Indicators.Data_Status='PROCESS as MOD'` via Bulk API
  - remove from `indicatorQueue` and add to `processedQueue`

### Daily Scripts:
1. *Eloqua_Contacts.Indicators_Refresh.py*
  - Retrieve a max of 80k Contacts.Indicators records from Eloqua where `Contacts.Indicators.Updated_Timestamp>180 days ago` and `Contacts.Indicators.Data_Status=='PROCESSED'`
  - set `Contacts.Indicators.Data_Status='PROCESS as MOD'`
  - Import records back to Eloqua via Bulk API

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

### Eloqua_Contacts_UpdateContactsIndicators.py
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts_DWM_INDICATORS_YYYY_MM_DD.log`
  - Explicitly logged runtime info
  - Accounted for exceptions
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts_UpdateContactsIndicators_Console_YYYY_MM_DD.log`
  - Runtime console output (including uncaught exceptions)
- Prometheus metrics (SLI):
  - *last_success_unixtime*: Last time of successful run
  - *total_seconds*: # of seconds to complete entire script
  - *total_records_total*: # of records processed
  - *total_records_errored*: # of records from batches which received an an error on import
  - *total_records_warning*: # of records from batches which received a warning on import
  - *total_records_success*: # of records which successfully imported to Eloqua

### Eloqua_Contacts.Indicators_Refresh.py
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts.Indicators_Refresh_YYYY_MM_DD.log`
  - Explicitly logged runtime info
  - Accounted for exceptions
- Logfile: `$OPENSHIFT_LOG_DIR/Eloqua_Contacts.Indicators_Refresh_Console_YYYY_MM_DD.log`
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

This implementation use ITOS (Red Hat IT-Hosted Openshift v2; comparable to Openshift Enterprise). Using the Openshift PaaS is a good rapid deployment solution in that it's fast and consistent in setup.

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

# Testing and Deployment

Best practices for testing in a Openshift DEV environment, then promoting to and Openshift PROD environment.

## Testing in DEV

- Test under database load by replicating prod DB
  + New features interacting with MongoDB may require additional indexing; testing with a full data replication has a greater chance of catching these issues
  1. Establish port forward to PROD:
    ```
    rhc port-forward dwmops -n PRODUCTION_NAMESPACE
    ```
  2. In a separate terminal:
    ```
    mongodump --port 12345
    ```
  3. Kill original port forward
  4. Establish port forward to DEV:
    ```
    rhc port-forward dwmops -n DEV_NAMESPACE
    ```
  5. In a separate terminal:
    ```
    mongorestore
    ```
- Ensure `runscripts` are uncommented for non-PROD environments
  + In DEV, `runscripts` for non-PROD should normally be commented out to avoid extra load on Eloqua's Bulk API  
- Wait up to 2 hours for next load from Eloqua
- Monitor queues via Prometheus to ensure proper flow
- If testing features expecting a different return result, check sample data from the final queue and the `dwmdev.contactHistory` collection to ensure proper application of business rules

## Deployment to PROD

- SSH into the gear and manually comment out python command in `runscripts/halfhour_getdwm.sh`
- Wait until all queues have been emptied
- Manually backup MongoDB
- Create a new release using `git flow release start vX.Y.Z`
- Populate any relevant release notes in the `CHANGELOG.md`
- Update the version in `setup.py`
- Finish release using `git flow release finish vX.Y.Z`
- Verify that PROD app `deployment-branch==master`
- Push to PROD
- Monitor queues regularly for next 8 hours, then next 2 mornings, to ensure proper data flow

## Rollback procedure

- Set deployment branch to previous stable release `rhc app-configure dwmops -n PRODUCTION_NAMESPACE --deployment-branch vA.B.C`
- `git push`

# TODO
- Build an API operating off the same MongoDB
