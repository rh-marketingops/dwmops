#!/bin/sh

if [ "$OPENSHIFT_NAMESPACE" == "marketing" ]; then
  nohup python $OPENSHIFT_REPO_DIR/Eloqua_Contacts_DWM.py > /dev/null 2>&1 &
else
  echo "not in 'marketing' namespace"
fi
