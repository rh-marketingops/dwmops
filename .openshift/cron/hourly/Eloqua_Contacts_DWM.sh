#!/bin/sh

if [ "$OPENSHIFT_NAMESPACE" == "marketing" ]; then
  nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts_DWM.py >> "$OPENSHIFT_LOG_DIR/Eloqua_Contacts_DWM_Console_$(date +%Y-%m-%d).log" 2>&1 &
else
  echo "not in 'marketing' namespace"
fi
