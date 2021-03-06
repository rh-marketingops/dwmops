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
jobName = 'Eloqua_Contacts_DWM_INDICATORS'
metricPrefix = 'BATCH_MINUTELY_ELOQUA_DWM_'

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
## Check queue size of waiting imports
###############################################################################

clientQueue = MongoClient(os.environ['MONGODB_URL'])

dbQueue = clientQueue['dwmqueue']

indicatorQueue = Queue(db = dbQueue, queueName = 'indicatorQueue')

size = indicatorQueue.getQueueSize()

logging.info('Records waiting in queue: ' + str(size))

## Setup
total = 0
warning = 0
errored = 0
success = 0

if size>0:

    job = indicatorQueue.next(job = jobName + '_' + format(datetime.now(), '%Y-%m-%d'), limit = 30000)

    if len(job)>0:

        emails = []

        for row in job:

            newRow = {}

            newRow['emailAddress'] = row['emailAddress']

            newRow['dataStatus'] = 'PROCESS as MOD'

            emails.append(newRow)

        fieldset = {}
        fieldset['emailAddress'] = '{{CustomObject[990].Field[18495]}}'
        fieldset['dataStatus'] = '{{CustomObject[990].Field[18496]}}'

        importDefName = 'dwm_triggerIndicators_' + str(datetime.now())
        importDef = elq.CreateDef(entity='customObjects', defType='imports', cdoID=990, fields=fieldset, defName=importDefName, identifierFieldName='emailAddress')
        logging.info("Import definition created: " + importDef['uri'])

        if env=='marketing':
            postInData = elq.PostSyncData(data=emails, defObject=importDef, maxPost=20000)
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

        processedQueue = Queue(db = dbQueue, queueName = 'processedQueue')

        if errored>0:
            erroredQueue = Queue(db = dbQueue, queueName = 'indicatorRefreshErroredQueue')
            erroredQueue.add(job, transfer=True)
        else:
            processedQueue.add(job, transfer=True)

        indicatorQueue.complete(job)

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
