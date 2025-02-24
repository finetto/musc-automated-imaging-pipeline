from pathlib import Path
import os
import sys
from datetime import datetime
import zipfile
import subprocess
import shutil
import json

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
rootdir = os.path.dirname(parentdir)

sys.path.insert(0, parentdir) 
from common import processing_settings
from common import database, database_settings
from common import notifications, notification_settings
from common import study, study_settings
from common import mri_proc_utils

# global variables
log_file_name = os.path.join(rootdir,"log","extract_data_log.txt")
log_file = None
original_stdout = None

# define open log file function
def open_log_file():

    global log_file
    global original_stdout

    # open log file
    log_file = open(log_file_name, "w")
    original_stdout = sys.stdout
    sys.stdout = log_file
    print("--------------------------")
    print("------ EXTRACT DATA ------")
    print(datetime.now())
    print("--------------------------")

# define close log file function
def close_log_file():

    # close log file
    sys.stdout = original_stdout
    log_file.close()

# define exit after error function
def terminate_after_error():

    print("\nTerminating script.")

    # close log file
    close_log_file()

    # send notification
    if mail_settings["errors"]["send_notification"]:
        notifications.send_email(mail_settings["errors"]["subject"],
                         "Attention: Errors were encountered during the execution of 'extract_data.py'\nPlease check the attached log file for further information.", 
                         mail_settings["errors"]["recipients"],
                         mail_settings["mail_server"]["address"],
                         mail_settings["mail_server"]["port"],
                         mail_settings["mail_server"]["user"],
                         mail_settings["mail_server"]["password"],
                         (log_file_name, ))

    sys.exit()

# open log file
open_log_file()

# get notification settings from file
mail_settings_file = os.path.join(rootdir,"settings","notification_settings.json")
mail_settings = notification_settings.load_from_file(mail_settings_file)
if mail_settings == -1:
    print("ERROR: Unable to load notification settings from \"" + mail_settings_file + "\".")
    terminate_after_error()

# get study settings from file
study_settings_file = os.path.join(rootdir,"settings","study_settings.json")
settings_study = study_settings.load_from_file(study_settings_file)
if settings_study == -1:
    print("ERROR: Unable to load study settings from \"" + study_settings_file + "\".")
    terminate_after_error()

# get processing settings from file
processing_settings_file = os.path.join(rootdir,"settings","processing_settings.json")
settings_processing = processing_settings.load_from_file(processing_settings_file)
if settings_processing == -1:
    print("ERROR: Unable to load processing settings from \"" + processing_settings_file + "\".")
    terminate_after_error()

# get database settings from file
db_settings_file = os.path.join(rootdir,"settings","database_settings.json")
db_settings = database_settings.load_from_file(db_settings_file)
if db_settings == -1:
    print("ERROR: Unable to load database settings from \"" + db_settings_file + "\".")
    terminate_after_error()

# connect to database
db = database.db(db_settings["db_path"])
db.n_default_query_attempts = db_settings["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

# find sessions for which data is available but not yet extracted and converted to nifti
# skip sessions that should be skipped
sessions_requiring_conversion = db.find_mri_sessions_requiring_conversion_to_nifti(exclude_skipped=True)
if sessions_requiring_conversion == -1: terminate_after_error()

for session in sessions_requiring_conversion:
    session_id = session["id"]
    participant_id = session["participant_id"]
    data_file = session["data_file"]

    # get folder for session
    session_name = Path(data_file).stem
    session_dir = Path(settings_processing["mri"]["workdir"]).joinpath(session_name)
    if not session_dir.exists():
        print("ERROR: Unable to find data folder for \"" + data_file + "\".")
        terminate_after_error()

    # extract zipped file
    zipped_file_path = session_dir.joinpath(data_file)
    zipped_file_extension = zipped_file_path.suffix
    if zipped_file_path.exists() and (zipped_file_extension == ".zip"):

        # remove previously unzipped files, if they are present
        unzipped_folder = session_dir.joinpath(zipped_file_path.stem)
        if unzipped_folder.exists():
            shutil.rmtree(unzipped_folder)

        # extract
        print("Extracting \"" + data_file + "\"")
        with zipfile.ZipFile(zipped_file_path,"r") as zipped_file:
            zipped_file.extractall(path=session_dir)

    # get dicom folder and move it to main session folder
    dicom_folder_src = session_dir.joinpath(session_name).joinpath("dicom")
    if not dicom_folder_src.exists():
        print("ERROR: Unable to find unzipped dicom data folder for session \"" + session_name + "\".")
        terminate_after_error()

    dicom_folder = session_dir.joinpath("dicom")
    if dicom_folder.exists():
        shutil.rmtree(dicom_folder)
    shutil.move(dicom_folder_src, dicom_folder)
    shutil.rmtree(session_dir.joinpath(session_name))

    # get conversion folder
    convert_folder = session_dir.joinpath("convert")
    if not convert_folder.exists():
        os.mkdir(convert_folder)

    # get nifti folder - make sure previous conversion results are removed
    nifti_folder = convert_folder.joinpath("nifti")
    if nifti_folder.exists():
        shutil.rmtree(nifti_folder)
    os.mkdir(nifti_folder)

    # get log folder
    log_folder = convert_folder.joinpath("log")
    if not log_folder.exists():
        os.mkdir(log_folder)

    # convert all data to NIfTI and log output
    dcm2niix_log_file = log_folder.joinpath("dcm2niix_log.txt")
    with open(dcm2niix_log_file, "w") as logfile:
        subprocess.run(["dcm2niix", "-u"], stdout=logfile) # check for updates
        subprocess.run(["dcm2niix", "-b", "y", 
                        "-ba", "y", 
                        "-z", "y", 
                        "-f", "%3s_%p", 
                        "-o",str(nifti_folder), 
                        str(dicom_folder)], 
                        stdout=logfile) # run conversion

    # move all converted files to respective series folder and collect series info
    all_converted_files = mri_proc_utils.list_converted_files(nifti_folder)
    all_series_numbers = []
    all_series_descriptions = []
    for file in all_converted_files:

        # get series number from file name
        series_info = mri_proc_utils.parse_converted_file_name(file)
        if series_info == -1:
            print("WARNING: invalid file found in nifti folder: \"" + file + "\".")
            continue
        series_number = series_info["series_number"]
        series_description = series_info["series_description"]

        # add info to list, if not already added
        if not series_number in all_series_numbers:
            all_series_numbers.append(series_number)
            all_series_descriptions.append(series_description)

        # move file to series folder
        series_folder = nifti_folder.joinpath(str(series_number).zfill(3))
        if not series_folder.exists():
            os.mkdir(series_folder)

        shutil.move(nifti_folder.joinpath(file), series_folder.joinpath(file))

    # add each series to the database
    for index, series_number in enumerate(all_series_numbers):

        series_description = all_series_descriptions[index]

        db.add_mri_series(participant_id=participant_id, session_id=session_id, series_number=series_number, description=series_description)

    # update session
    db.update_mri_session(session_id, converted_to_nifti_dt=datetime.now().timestamp())

    db.commit()


# close connection to database
db.close()

# close log file
print("Extract data complete")
close_log_file()