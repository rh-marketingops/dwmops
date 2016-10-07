from pyqm import Queue, clean
from pymongo import MongoClient
from datetime import datetime
import sys, os, logging
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

###############################################################################
## Setup logging
###############################################################################

## setup job name
jobName = 'CLEAN_QUEUE_DWM'
metricPrefix = 'BATCH_MINUTELY_ELOQUA_DWM_'

## Setup logging
logname = '/' + jobName + '_' + format(datetime.now(), '%Y-%m-%d') + '.log'
logging.basicConfig(filename=os.environ['OPENSHIFT_LOG_DIR'] + logname, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
jobStart = datetime.now()

###############################################################################
## Release 'stale' locked records and get queue sizes
###############################################################################

clientQueue = MongoClient(os.environ['MONGODB_URL'])

dbQueue = clientQueue['dwmqueue']

# get list of queues
queues = []
queueFind = dbQueue['queueList'].find()

for queue in queueFind:
    queues.append(queue['queueName'])

#logging.info("# of queues: " + str(len(queues)))

for row in queues:

    cq = Queue(db = dbQueue, queueName = row)

    queueSize = cq.getQueueSize()

    #logging.info(row + ' size: ' + str(queueSize))

    timeout = cq.timeout(t=300)

    #logging.info(row + ' timeout: ' + str(timeout))

    registry = CollectorRegistry()
    a = Gauge('QueueSize', 'Size of queue', registry=registry)
    a.set(queueSize)
    b = Gauge('QueueTimeout', 'Number of records timed out', registry=registry)
    b.set(queueSize)
    push_to_gateway(os.environ['PUSHGATEWAY'], job=jobName + '_' + row, registry=registry)
    del registry

# Send script success to pushgateway
registry = CollectorRegistry()
g = Gauge(metricPrefix + 'last_success_unixtime', 'Last time a batch job successfully finished', registry=registry)
g.set_to_current_time()
push_to_gateway(os.environ['PUSHGATEWAY'], job=jobName, registry=registry)
