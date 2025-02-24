#! /bin/bash

# get directory containing current script and directory from which script is called
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CALLING_DIR=$(pwd)

# move to script dir
cd $SCRIPT_DIR

# activate virtual environment
source .automated_pipeline_env/bin/activate

# call python scripts using its dedicated venv
echo "Starting Data Viewer GUI"
echo ""

python3 code/data_viewer_ui/data_viewer_ui.py

echo ""
echo "Done"

# deactivate virtual environment
deactivate

# move back to calling dir
cd $CALLING_DIR