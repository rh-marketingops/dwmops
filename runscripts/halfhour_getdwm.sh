#!/bin/sh

if [ "$OPENSHIFT_NAMESPACE" == "marketing" ]; then
  nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts_GetDWM.py >> "$OPENSHIFT_LOG_DIR/Eloqua_Contacts_GetDWM_Console_$(date +%Y-%m-%d).log" 2>&1 &
else
  echo "not PROD"
  #nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts_GetDWM.py >> "$OPENSHIFT_LOG_DIR/Eloqua_Contacts_GetDWM_Console_$(date +%Y-%m-%d).log" 2>&1 &
fi
