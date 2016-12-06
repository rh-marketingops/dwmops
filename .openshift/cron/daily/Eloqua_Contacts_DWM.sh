#!/bin/sh

if [ "$OPENSHIFT_NAMESPACE" == "marketing" ]; then
  nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts.Indicators_Refresh.py >> "$OPENSHIFT_LOG_DIR/Eloqua_Contacts.Indicators_Refresh_Console_$(date +%Y-%m-%d).log" 2>&1 &
else
  echo "not PROD"
  nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts.Indicators_Refresh.py >> "$OPENSHIFT_LOG_DIR/Eloqua_Contacts.Indicators_Refresh_Console_$(date +%Y-%m-%d).log" 2>&1 &
fi
