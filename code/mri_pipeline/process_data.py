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
log_file_name = os.path.join(rootdir,"log","process_data_log.txt")
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
    print("------ PROCESS DATA ------")
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
                         "Attention: Errors were encountered during the execution of 'process_data.py'\nPlease check the attached log file for further information.", 
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

# get dcm2bids config from file
dcm2bids_config_file = os.path.join(rootdir,"settings","dcm2bids_config.json")
config_dcm2bids = mri_proc_utils.parse_dcm2bids_config(dcm2bids_config_file)
if config_dcm2bids == -1:
    print("ERROR: Unable to load dcm2bids configuration from \"" + dcm2bids_config_file + "\".")
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

# find sessions for which data is available but not yet converted to BIDS format
sessions_requiring_conversion = db.find_mri_sessions_requiring_conversion_to_bids(exclude_skipped=True)
if sessions_requiring_conversion == -1: terminate_after_error()

for session in sessions_requiring_conversion:
    session_id = session["id"]
    participant_id = session["participant_id"]
    data_file = session["data_file"]
    participant_session_id = session["participant_session_id"]

    # get participant data
    participant = db.get_participant_data(id=participant_id, return_only_first=True)
    if participant == -1:
        print("ERROR: Unable to get participant data for \"" + data_file + "\".")
        terminate_after_error()

    if participant==None:
        print("WARNING: No participant selected for \"" + data_file + "\".")
        continue

    # check participant and session ID
    participant_study_id = participant["study_id"]
    if (participant_study_id == None) or (participant_study_id == ""):
        print("WARNING: Invalid participant ID for \"" + data_file + "\".")
        continue
    if (participant_session_id == None) or (participant_session_id == ""):
        print("WARNING: Invalid session ID for \"" + data_file + "\".")
        continue

    # get series in session
    session_series = db.get_mri_series_data(session_id=session["id"])
    if session_series == -1:
        print("ERROR: Unable to get series information for \"" + data_file + "\".")
        terminate_after_error()
    
    if len(session_series)<1:
        print("WARNING: No series found for \"" + data_file + "\".")
        continue

    # get folder for session
    session_name = Path(data_file).stem
    session_dir = Path(settings_processing["mri"]["workdir"]).joinpath(session_name)
    if not session_dir.exists():
        print("WARNING: Unable to find data folder for \"" + data_file + "\".")
        continue

    # get conversion folder
    convert_folder = session_dir.joinpath("convert")
    if not convert_folder.exists():
        print("WARNING: Unable to find converted data folder for \"" + data_file + "\".")
        continue

    # get nifti folder
    nifti_folder = convert_folder.joinpath("nifti")
    if not nifti_folder.exists():
        print("WARNING: Unable to find NIfTI data folder for \"" + data_file + "\".")
        continue

    # get BIDS folder - make sure previous conversion results are removed
    bids_folder = convert_folder.joinpath("bids")
    if bids_folder.exists():
        shutil.rmtree(bids_folder)
    os.mkdir(bids_folder)

    # get log folder
    log_folder = convert_folder.joinpath("log")
    if not log_folder.exists():
        os.mkdir(log_folder)

    dcm2bids_log_file = log_folder.joinpath("dcm2bids_log.txt")
    with open(dcm2bids_log_file, "w") as logfile:
        subprocess.run(["dcm2bids", "-v"], stdout=logfile) # report version

        # convert each series
        for series in session_series:

            # get series folder
            series_folder = nifti_folder.joinpath(str(series["series_number"]).zfill(3))
            if not series_folder.exists():
                print("WARNING: Unable to find series " + str(series["series_number"]) + " folder for \"" + data_file + "\".")
                continue

            # check if series should be skipped
            if series["skip_processing"]==1:
                continue

            # check if series was already converted
            if series["data_converted_dt"] != None:
                continue

            # convert all data to NIfTI and log output
            subprocess.run(["dcm2bids", "-d", str(series_folder), 
                            "-p", participant_study_id, 
                            "-s", participant_session_id, 
                            "-c", dcm2bids_config_file, 
                            "-o",str(bids_folder), 
                            "--skip_dcm2niix", "--clobber"], 
                            stdout=logfile) # run BIDS conversion
                
            # update series
            db.update_mri_series(series["id"], data_converted_dt=datetime.now().timestamp())
            db.commit()

    # get converted data folder for this participant
    participant_data_folder = bids_folder.joinpath(participant_study_id)
    if not participant_data_folder.exists():
        print("WARNING: Unable to find converted BIDS data folder for \"" + data_file + "\".")
        continue

    # deidentify data (if possible)
    participant_deidentified_id = participant["deidentified_id"]
    participant_deidentified_data_folder = bids_folder.joinpath(participant_deidentified_id)
    if settings_study["deidentify_data"] and (participant_deidentified_id != None) and (participant_deidentified_id != ""):
        
        # rename files and folders
        mri_proc_utils.deidentify_files_and_folders(str(participant_data_folder),
                                             str(participant_deidentified_data_folder), 
                                             participant_study_id, 
                                             participant_deidentified_id)
        
        # deface T1 and T2 images
        anat_folder = participant_deidentified_data_folder.joinpath(participant_session_id).joinpath("anat")
        if anat_folder.exists():
            pydeface_log_file = log_folder.joinpath("pydeface_log.txt")
            files = mri_proc_utils.list_converted_files(str(anat_folder))
            with open(pydeface_log_file, "w") as logfile:
                for file in files:
                    if file.endswith(".nii.gz"):
                        file_path = str(anat_folder.joinpath(file))
                        subprocess.run(["pydeface",
                                        file_path,
                                        "--outfile", file_path,
                                        "--force"],
                                        stdout=logfile)
                                                        

    # copy sourcedata
    sourcedata_dir = Path(settings_processing["mri"]["sourcedata_dir"])
    if not sourcedata_dir.exists():
        os.mkdir(sourcedata_dir)
    
    subject_dstdir = sourcedata_dir.joinpath(participant_study_id)
    if not subject_dstdir.exists():
        os.mkdir(subject_dstdir)

    session_dstdir = subject_dstdir.joinpath(participant_session_id)
    if not session_dstdir.exists():
        os.mkdir(session_dstdir)

    data_file_srcpath = session_dir.joinpath(data_file)
    summary_file_srcpath = session_dir.joinpath(session["summary_file"])

    if data_file_srcpath.exists():
        data_file_dstpath = session_dstdir.joinpath(data_file)
        shutil.copyfile(str(data_file_srcpath), str(data_file_dstpath))

    if summary_file_srcpath.exists():
        summary_file_dstpath = session_dstdir.joinpath(session["summary_file"])
        shutil.copyfile(str(summary_file_srcpath), str(summary_file_dstpath))

    # copy BIDS data
    data_dir = Path(settings_processing["mri"]["data_dir"])
    if not data_dir.exists():
        os.mkdir(data_dir)
    
    subject_dstdir = data_dir.joinpath(participant_study_id)
    if not subject_dstdir.exists():
        os.mkdir(subject_dstdir)

    session_dstdir = subject_dstdir.joinpath(participant_session_id)
    if session_dstdir.exists():
        shutil.rmtree(session_dstdir)

    session_srcdir = participant_data_folder.joinpath(participant_session_id)
    if session_srcdir.exists():
        shutil.copytree(session_srcdir, session_dstdir)

    # copy deidentified BIDS data
    if settings_study["deidentify_data"] and (participant_deidentified_id != None) and (participant_deidentified_id != ""):
        data_dir = Path(settings_processing["mri"]["deidentified_data_dir"])
        if not data_dir.exists():
            os.mkdir(data_dir)
        
        subject_dstdir = data_dir.joinpath(participant_deidentified_id)
        if not subject_dstdir.exists():
            os.mkdir(subject_dstdir)

        session_dstdir = subject_dstdir.joinpath(participant_session_id)
        if session_dstdir.exists():
            shutil.rmtree(session_dstdir)

        session_srcdir = participant_deidentified_data_folder.joinpath(participant_session_id)
        if session_srcdir.exists():
            shutil.copytree(session_srcdir, session_dstdir)

    # update session
    db.update_mri_session(session_id, data_converted_dt=datetime.now().timestamp())

    db.commit()


# close connection to database
db.close()

# close log file
print("Process data complete")
close_log_file()


