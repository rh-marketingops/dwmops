#!bin/sh

find $OPENSHIFT_LOG_DIR/ -type f -mtime +14 -delete
