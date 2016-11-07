from pyeloqua import Eloqua
from datetime import datetime, timedelta
import sys, os, logging
from pymongo import MongoClient
from pyqm import Queue, clean
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

###############################################################################
## Setup logging
###############################################################################

## setup job name
jobName = 'Eloqua_Contacts.Indicators_Refresh'
metricPrefix = 'BATCH_DAILY_ELOQUA_DWM_'

## Setup logging
logname = '/' + jobName + '_' + format(datetime.now(), '%Y-%m-%d') + '.log'
logging.basicConfig(filename=os.environ['OPENSHIFT_LOG_DIR'] + logname, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
jobStart = datetime.now()

###############################################################################
## Setup Eloqua session
###############################################################################

elq = Eloqua(username=os.environ['ELOQUA_USER'], password=os.environ['ELOQUA_PASSWORD'], company=os.environ['ELOQUA_COMPANY'])
logging.info("Eloqua session established")

###############################################################################
## Export contacts from Eloqua
###############################################################################

fieldset = {}
fieldset['emailAddress'] = '{{CustomObject[990].Field[18495]}}'
fieldset['dataStatus'] = '{{CustomObject[990].Field[18496]}}'

## Set filter
time = datetime.strftime((datetime.now() - timedelta(days=180)), '%Y-%m-%d %H:%M:%S')
myFilter = elq.FilterDateRange(entity='customObjects', field='Contacts.Indicators.Updated_Timestamp', start='2010-01-01 01:00:00', end=time, cdoID=990)

myFilter += " AND '{{CustomObject[990].Field[18496]}}' = 'PROCESSED' "

# create bulk export
exportDefName = jobName + str(datetime.now())
exportDef = elq.CreateDef(defType='exports', entity='customObjects', cdoID=990, fields=fieldset, filters = myFilter, defName=exportDefName)

logging.info("export definition created: " + exportDef['uri'])

## Create sync
exportSync = elq.CreateSync(defObject=exportDef)
logging.info("export sync started: " + exportSync['uri'])
status = elq.CheckSyncStatus(syncObject=exportSync)
logging.info("sync successful; retreiving data")

## Retrieve data
data = elq.GetSyncedData(defObject=exportDef, retrieveLimit=80000)
logging.info("# of records:" + str(len(data)))

## Setup logging vars
total = len(data)

## Setup
warning = 0
errored = 0
success = 0

if total>0:

    for row in data:

        row['dataStatus'] = 'PROCESS as MOD'

    importDefName = jobName + str(datetime.now())
    importDef = elq.CreateDef(defType='imports', entity='customObjects', cdoID=990, fields=fieldset, defName=importDefName, identifierFieldName='emailAddress')
    logging.info("Import definition created: " + importDef['uri'])

    postInData = elq.PostSyncData(data=data, defObject=importDef, maxPost=20000)
    logging.info("Data import finished: " + str(datetime.now()))

    ## agg stats about success of import
    for row in postInData:
        total += row['count']
        if row['status']=='success':
            success += row['count']
        if row['status'] == 'warning':
            warning += row['count']
            logging.info("Sync finished with status 'warning': " + str(row['count']) + " records; " + row['uri'])
        if row['status'] == 'errored':
            errored += row['count']
            logging.info("Sync finished with status 'errored': " + str(row['count']) + " records; " + row['uri'])


jobEnd = datetime.now()
jobTime = (jobEnd-jobStart).total_seconds()

## Push monitoring stats to Prometheus
if env=='marketing':
    registry = CollectorRegistry()
    g = Gauge(metricPrefix + 'last_success_unixtime', 'Last time a batch job successfully finished', registry=registry)
    g.set_to_current_time()
    l = Gauge(metricPrefix + 'total_seconds', 'Total number of seconds to complete job', registry=registry)
    l.set(jobTime)
    t = Gauge(metricPrefix + 'total_records_total', 'Total number of records processed in last batch', registry=registry)
    t.set(total)
    e = Gauge(metricPrefix + 'total_records_errored', 'Total number of records errored in last batch', registry=registry)
    e.set(errored)
    w = Gauge(metricPrefix + 'total_records_warning', 'Total number of records warned in last batch', registry=registry)
    w.set(warning)
    s = Gauge(metricPrefix + 'total_records_success', 'Total number of records successful in last batch', registry=registry)
    s.set(success)

    push_to_gateway(os.environ['PUSHGATEWAY'], job=jobName, registry=registry)
