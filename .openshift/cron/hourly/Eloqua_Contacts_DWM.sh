#!/bin/sh

if [ "$OPENSHIFT_NAMESPACE" == "marketing" ]; then
  nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts_DWM.py >> $OPENSHIFT_LOG_DIR/date +"%Y-%m-%d""-Eloqua_DWM_console.log" 2>&1 &
else
  echo "not in 'marketing' namespace"
fi
