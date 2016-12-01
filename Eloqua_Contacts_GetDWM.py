from pyeloqua import Eloqua
from datetime import datetime
import sys, os, logging
from pymongo import MongoClient
from pyqm import Queue
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

###############################################################################
## Setup logging
###############################################################################

## setup job name
jobName = 'Eloqua_Contacts_DWM_GET'
metricPrefix = 'BATCH_HOURLY_ELOQUA_DWM_'

## Setup logging
logname = '/' + jobName + '_' + format(datetime.now(), '%Y-%m-%d') + '.log'
logging.basicConfig(filename=os.environ['OPENSHIFT_LOG_DIR'] + logname, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
jobStart = datetime.now()

env = os.environ['OPENSHIFT_NAMESPACE']

###############################################################################
## Setup Eloqua session
###############################################################################

elq = Eloqua(username=os.environ['ELOQUA_USER'], password=os.environ['ELOQUA_PASSWORD'], company=os.environ['ELOQUA_COMPANY'])
logging.info("Eloqua session established")

###############################################################################
## Export contacts from Eloqua
###############################################################################

## import field set; store this in a separate file so we can edit them without touching this script
from Eloqua_Contacts_ExportFields import fieldset

## Set filter
if env=='marketing':
    myFilter = elq.FilterExists(name='DWM - Export Queue', existsType='ContactList')
else:
    myFilter = elq.FilterExists(name='DWM - Export Queue TEST', existsType='ContactList')

# create bulk export
exportDefName = jobName + str(datetime.now())
if env=='marketing':
    syncAction = elq.CreateSyncAction(action='remove', listName='DWM - Export Queue', listType='contacts')
else:
    syncAction = elq.CreateSyncAction(action='remove', listName='DWM - Export Queue TEST', listType='contacts')

exportDef = elq.CreateDef(defType='exports', entity='contacts', fields=fieldset, filters = myFilter, defName=exportDefName, syncActions=[syncAction])

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

if len(data)>0:

    logging.info("Add to 'dwmQueue'")

    client = MongoClient(os.environ['MONGODB_URL'])

    db = client['dwmqueue']

    exportQueue = Queue(db = db, queueName = 'dwmQueue')

    exportQueue.add(data, batchName=jobName + ' ' + format(datetime.now(), '%Y-%m-%d %H:%M:%S'))

    logging.info("Added to 'dwmQueue'")

else:

    logging.info("Aw, theres no records here. gosh darn")

jobEnd = datetime.now()
jobTime = (jobEnd-jobStart).total_seconds()

registry = CollectorRegistry()
g = Gauge(metricPrefix + 'last_success_unixtime', 'Last time a batch job successfully finished', registry=registry)
g.set_to_current_time()
l = Gauge(metricPrefix + 'total_seconds', 'Total number of seconds to complete job', registry=registry)
l.set(jobTime)
t = Gauge(metricPrefix + 'total_records_total', 'Total number of records processed in last batch', registry=registry)
t.set(total)

push_to_gateway(os.environ['PUSHGATEWAY'], job=jobName, registry=registry)
