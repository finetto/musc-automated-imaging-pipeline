#! /bin/bash

# get directory containing current script and directory from which script is called
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CALLING_DIR=$(pwd)

# move to script dir
cd $SCRIPT_DIR

# activate virtual environment
source .automated_pipeline_env/bin/activate

# call python scripts using its dedicated venv
echo "Started automated MRI pipeline"
echo ""

echo "Running CBI SYNC script ..."
python3 code/mri_pipeline/cbi_sync.py
echo "Done"

echo ""
echo "Running data extraction script ..."
python3 code/mri_pipeline/extract_data.py
echo "Done"

echo ""
echo "Running data validation script ..."
python3 code/mri_pipeline/validate_data.py
echo "Done"

echo ""
echo "Running notification script ..."
python3 code/mri_pipeline/send_validation_notifications.py
echo "Done"

echo ""
echo "Running data validation with summary script ..."
python3 code/mri_pipeline/validate_data_with_summary.py
echo "Done"

echo ""
echo "Running data conversion script ..."
python3 code/mri_pipeline/process_data.py
echo "Done"

echo ""
echo "Running data upload script ..."
python3 code/mri_pipeline/upload_data.py
echo "Done"

echo ""
echo "Running data cleanup script ..."
python3 code/mri_pipeline/cleanup_data.py
echo "Done"

echo ""
echo "MRI pipeline completed"

# deactivate virtual environment
deactivate

# move back to calling dir
cd $CALLING_DIR