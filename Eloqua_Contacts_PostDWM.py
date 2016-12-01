from pyeloqua import Eloqua
from datetime import datetime
import sys, os, logging
from pymongo import MongoClient
from pyqm import Queue, clean
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

###############################################################################
## Setup logging
###############################################################################

## setup job name
jobName = 'Eloqua_Contacts_DWM_POST'
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
## Import contacts to Eloqua
###############################################################################

## import field set; store this in a separate file so we can edit them without touching this script
from Eloqua_Contacts_ExportFields import fieldset

###############################################################################
## Check queue size of waiting imports
###############################################################################

clientQueue = MongoClient(os.environ['MONGODB_URL'])

dbQueue = clientQueue['dwmqueue']

processedQueue = Queue(db = dbQueue, queueName = 'processedQueue')

size = processedQueue.getQueueSize()

logging.info('Records waiting in queue: ' + str(size))

## Setup
total = 0
warning = 0
errored = 0
success = 0



if size>0:

    job = processedQueue.next(job = jobName + '_' + format(datetime.now(), '%Y-%m-%d'), limit = 30000)

    if len(job)>0:

        jobClean = clean(job)

        ###############################################################################
        ## Import data back to Eloqua
        ###############################################################################

        # create sync action to remove from shared list on import

        syncAction = elq.CreateSyncAction(action='remove', listName='DWM - Processing Queue', listType='contacts')

        importDefName = 'dwmtest' + str(datetime.now())
        importDef = elq.CreateDef(entity='contacts', defType='imports', fields=fieldset, defName=importDefName, identifierFieldName='emailAddress', syncActions=[syncAction])
        logging.info("Import definition created: " + importDef['uri'])
        if env=='marketing':
            postInData = elq.PostSyncData(data=jobClean, defObject=importDef, maxPost=20000)
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
            logging.info('not PROD environment, not POSTing to Eloqua')

        # Adding this to deal with records where there is an error on import
        if errored>0:
            erroredQueue = Queue(db = dbQueue, queueName = 'dwmPOSTErroredQueue')
            erroredQueue.add(job, transfer=True)

        processedQueue.complete(job, completeBatch=True)

    else:

        logging.info('no records to send... taking the day off!!!')

else:

    logging.info('no records to send... taking the day off!!!')

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
