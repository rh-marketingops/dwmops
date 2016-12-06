#!/bin/bash

## This is a keepalive script. Since no web traffic should be going to the Openshift app, it will end up idling
## When that happens, cron jobs stop and the DB shuts down
## This script pings the url once an hour to keep it alive
PATH=/bin:/usr/bin:/usr/sbin
app_url=http://$OPENSHIFT_APP_DNS/

curl --insecure --location --silent --fail "$app_url" >/dev/null
