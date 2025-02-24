#! /bin/bash

echo "Uninstalling the automated pipeline"
echo "------------------------------------------------------------"
echo ""

# get directory containing current script and directory from which script is called
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CALLING_DIR=$(pwd)

# move to script dir
cd $SCRIPT_DIR

# set cronjob to run pipeline at the beginning of every hour
echo "Removing cronjobs"
crontab -l | grep -v "${SCRIPT_DIR}/run_mri_pipeline.sh" | crontab -

echo ""
echo "------------------------------------------------------------"
echo "Uninstallation complete"

# move back to calling dir
cd $CALLING_DIR