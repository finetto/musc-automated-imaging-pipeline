#! /bin/bash

echo "Installing all tools necessary to run the automated pipeline"
echo "------------------------------------------------------------"
echo "Please note: Anaconda conflicts with PyQt. If Anaconda is"
echo "             installed, the data viewer software may not"
echo "             close properly. To avoid issues, please remove"
echo "             Anaconda and use the standard python3 package."
echo "------------------------------------------------------------"
echo ""

# get directory containing current script and directory from which script is called
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CALLING_DIR=$(pwd)

# move to script dir
cd $SCRIPT_DIR

# install needed packages
echo "Installing all needed packages"
sudo apt update
sudo apt install cmake gcc g++ wget\
  python3 python3-pip \
  dc mesa-utils gedit pulseaudio libquadmath0 libgtk2.0-0 firefox libgomp1 \
  libxcb-cursor-dev \
  -y
echo ""

# install dedicated python virtual environment
echo "Installing dedicated virtual environment"
sudo pip install virtualenv
if [ -d .automated_pipeline_env ] ; then
echo ""
  read -p "Detected existing virtual environment. Would you like to delete it and create it again [y/n]? " user_input
  if [[ "${user_input,,}" == "y" || "${user_input,,}" == "yes" ]] ; then
    echo "Deleting existing virtual environment ..."
    rm -rf .automated_pipeline_env
  fi
fi
if [ ! -d .automated_pipeline_env ] ; then
  virtualenv .automated_pipeline_env
fi
echo ""

# define CXX environment variable - necessary to install dcm2niix
export CXX=/usr/bin/g++

# install necessary python packages
echo "Installing python packages"
source .automated_pipeline_env/bin/activate
pip install -r requirements.txt
echo ""

# install FSL
if [ -z $FSLDIR ] ; then
  echo "Installing FSL"
  wget https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/releases/fslinstaller.py
  python3 fslinstaller.py -d $HOME/fsl -o
  rm fslinstaller.py
  echo ""
  echo "Remember to restart your terminal to activate FSL!"
  echo ""
else 
  echo "Detected FSL installation in $FSLDIR. Skipping new installation."
  echo ""
fi

# create necessary directories
echo "Creating all necessary directories"
if [ ! -d log ] ; then
  mkdir log
fi
if [ ! -d settings ] ; then
  mkdir settings
fi
echo ""

# set cronjob to run pipeline at the beginning of every hour
echo "Configuring cronjobs"
CMD="0 * * * * /usr/bin/flock -n $SCRIPT_DIR/run_mri_pipeline.lock $SCRIPT_DIR/run_mri_pipeline.sh"
(crontab -l ; echo "$CMD") 2>/dev/null | sort - | uniq - | crontab -


# deactivate python environment
deactivate

echo ""
echo "------------------------------------------------------------"
echo "Installation complete"

# move back to calling dir
cd $CALLING_DIR
