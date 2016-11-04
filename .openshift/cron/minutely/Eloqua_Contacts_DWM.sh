#!/bin/sh

if [ "$OPENSHIFT_NAMESPACE" == "marketing" ]; then
  nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts_RunDWM.py >> "$OPENSHIFT_LOG_DIR/Eloqua_Contacts_RunDWM_Console_$(date +%Y-%m-%d).log" 2>&1 &
  nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts_CleanQueues.py >> "$OPENSHIFT_LOG_DIR/Eloqua_Contacts_CleanQueues_Console_$(date +%Y-%m-%d).log" 2>&1 &
  nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts_UpdateContactsIndicators.py >> "$OPENSHIFT_LOG_DIR/Eloqua_Contacts_UpdateContactsIndicators_Console_$(date +%Y-%m-%d).log" 2>&1 &
else
  echo "not in 'marketing' namespace"
fi
