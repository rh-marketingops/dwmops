import dwm
from pyeloqua import Eloqua
from datetime import datetime
import sys, os, logging
from pymongo import MongoClient
from collections import OrderedDict
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

###############################################################################
## Load custom functions
###############################################################################

from custom import CleanZipcodeUS, CleanAnnualRevenue

###############################################################################
## Setup logging
###############################################################################

## setup job name
jobName = 'Eloqua_Contacts_DWM'
metricPrefix = 'BATCH_HOURLY_ELOQUA_DWM_'

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

## import field set; store this in a separate file so we can edit them without touching this script
from Eloqua_Contacts_ExportFields import fieldset

## Set filter
myFilter = elq.FilterExists(name='DWM: Python Feeder', existsType='ContactFilter')

# create bulk export
exportDefName = jobName + str(datetime.now())
exportDef = elq.CreateDef(defType='exports', entity='contacts', fields=fieldset, filters = myFilter, defName=exportDefName)
logging.info("export definition created: " + exportDef['uri'])

## Create sync
exportSync = elq.CreateSync(defObject=exportDef)
logging.info("export sync started: " + exportSync['uri'])
status = elq.CheckSyncStatus(syncObject=exportSync)
logging.info("sync successful; retreiving data")

## Retrieve data
data = elq.GetSyncedData(defObject=exportDef, retrieveLimit=35000)
logging.info("# of records:" + str(len(data)))

## Setup
total = 0
warning = 0
errored = 0
success = 0

## Only do the processing if there are contacts to process
if len(data)>0:

    ###############################################################################
    ## Retrieve DWM configuration
    ###############################################################################

    ## In some cases (including ours), the actual ordering of the 'fields' subdoc of config is order-dependant
    ## i.e., if the "Persona" field is dependant on having a valid value in "Job Role", then any cleaning rules should be applied to "Job Role" first

    ## To make sure this is the case, we connect to MongoDB first specifying document_class=OrderedDict
    ## This will preserve the ordering of fields

    ## Reason for using a different connection: specifying document_class in the MongoClient will slowwwww the rest of the queries for DWM.
    ## So, just close it out and create a new connection to pass to DWM

    client = MongoClient(os.environ['MONGODB_URL'], document_class=OrderedDict)
    db = client['dwmdev']

    config = db.config.find_one({"configName": "Eloqua_Contacts_DWM"})

    logging.info("Retrieved config from MongoDB as an OrderedDict")

    client.close()

    ###############################################################################
    ## Run the DWM
    ###############################################################################

    ## connect to mongo
    client = MongoClient(os.environ['MONGODB_URL'])
    db = client['dwmdev']
    logging.info("Connected to mongo")

    ## Run DWM
    dataOut = dwm.dwmAll(data=data, db=db, config=config, udfNamespace=__name__)

    client.close()

    ###############################################################################
    ## Import data back to Eloqua
    ###############################################################################

    importDefName = 'dwmtest' + str(datetime.now())
    importDef = elq.CreateDef(entity='contacts', defType='imports', fields=fieldset, defName=importDefName, identifierFieldName='emailAddress')
    logging.info("Import definition created: " + importDef['uri'])
    postInData = elq.PostSyncData(data=dataOut, defObject=importDef, maxPost=20000)
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

else:
    logging.info("No data :(")

jobEnd = datetime.now()
jobTime = (jobEnd-jobStart).total_seconds()

## Push monitoring stats to Prometheus
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
