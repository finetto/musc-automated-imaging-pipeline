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
from common import box_client, box_sync_settings

# global variables
log_file_name = os.path.join(rootdir,"log","upload_data_log.txt")
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
    print("------- UPLOAD DATA ------")
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
                         "Attention: Errors were encountered during the execution of 'upload_data.py'\nPlease check the attached log file for further information.", 
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

# get box sync settings from file
box_settings_file = os.path.join(rootdir,"settings","box_sync_settings.json")
settings_box = box_sync_settings.load_from_file(box_settings_file)
if settings_box == -1:
    print("ERROR: Unable to load Box settings from \"" + box_settings_file + "\".")
    terminate_after_error()

# check if Box sync is enabled
if not settings_box["use_box_sync"]:
    print("\nBox sync disabled.\nTerminating script.")
    close_log_file()
    sys.exit()

# check if any upload folders were specified
if (settings_box["sourcedata_dir_id"] == None) or (settings_box["sourcedata_dir_id"] == ""):
    sourcedata_upload_enabled = False
else:
    sourcedata_upload_enabled = True

if (settings_box["data_dir_id"] == None) or (settings_box["data_dir_id"] == ""):
    data_upload_enabled = False
else:
    data_upload_enabled = True
    
if (settings_box["deidentified_data_dir_id"] == None) or (settings_box["deidentified_data_dir_id"] == ""):
    deidentified_data_upload_enabled = False
else:
    deidentified_data_upload_enabled = True

if (not sourcedata_upload_enabled) and (not data_upload_enabled) and (not deidentified_data_upload_enabled):
    print("\nBox upload disabled.\nTerminating script.")
    sys.exit()

# connect to database
db = database.db(db_settings["db_path"])
db.n_default_query_attempts = db_settings["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

# connect to box
box = box_client.box_client()
success = box.connect(
    client_id=settings_box["authentication"]["client_id"],
    client_secret=settings_box["authentication"]["client_secret"],
    user_id=settings_box["authentication"]["user_id"]
    )
if not success:
    print("ERROR: Unable to connect to Box.")
    terminate_after_error()

# check existence of upload folders
if sourcedata_upload_enabled and (not box.folder_exists(settings_box["sourcedata_dir_id"])):
    print("ERROR: Sourcedata folder does not exist on Box.")
    terminate_after_error()

if data_upload_enabled and (not box.folder_exists(settings_box["data_dir_id"])):
    print("ERROR: Data folder does not exist on Box.")
    terminate_after_error()

if deidentified_data_upload_enabled and settings_study["deidentify_data"] and (not box.folder_exists(settings_box["deidentified_data_dir_id"])):
    print("ERROR: Deidentified data folder does not exist on Box.")
    terminate_after_error()

# find sessions for which data was converted to BIDS but not yet uploaded
sessions_requiring_upload = db.find_mri_sessions_requiring_upload(exclude_skipped=True)
if sessions_requiring_upload == -1: terminate_after_error()


issues_during_upload = False
for session in sessions_requiring_upload:
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
        issues_during_upload = True
        continue

    # check participant and session ID
    participant_study_id = participant["study_id"]
    if (participant_study_id == None) or (participant_study_id == ""):
        print("WARNING: Invalid participant ID for \"" + data_file + "\".")
        issues_during_upload = True
        continue
    if (participant_session_id == None) or (participant_session_id == ""):
        print("WARNING: Invalid session ID for \"" + data_file + "\".")
        issues_during_upload = True
        continue

    # get series in session
    session_series = db.get_mri_series_data(session_id=session["id"])
    if session_series == -1:
        print("ERROR: Unable to get series information for \"" + data_file + "\".")
        terminate_after_error()
    
    if len(session_series)<1:
        print("WARNING: No series found for \"" + data_file + "\".")
        issues_during_upload = True
        continue

    # get folder for session
    session_name = Path(data_file).stem
    session_dir = Path(settings_processing["mri"]["workdir"]).joinpath(session_name)
    if not session_dir.exists():
        print("WARNING: Unable to find data folder for \"" + data_file + "\".")
        issues_during_upload = True
        continue

    # get conversion folder
    convert_folder = session_dir.joinpath("convert")
    if not convert_folder.exists():
        print("WARNING: Unable to find converted data folder for \"" + data_file + "\".")
        issues_during_upload = True
        continue

    # get BIDS folder
    bids_folder = convert_folder.joinpath("bids")
    if not bids_folder.exists():
        print("WARNING: Unable to find BIDS data folder for \"" + data_file + "\".")
        issues_during_upload = True
        continue

    # get log folder
    log_folder = convert_folder.joinpath("log")
    if not log_folder.exists():
        os.mkdir(log_folder)

    # get converted data folder for this participant
    participant_data_folder = bids_folder.joinpath(participant_study_id)
    if not participant_data_folder.exists():
        print("WARNING: Unable to find converted BIDS data folder for \"" + data_file + "\".")
        issues_during_upload = True
        continue

    # get deidentified data folder
    participant_deidentified_id = participant["deidentified_id"]
    participant_deidentified_data_folder = bids_folder.joinpath(participant_deidentified_id)
    if settings_study["deidentify_data"] and (participant_deidentified_id != None) and (participant_deidentified_id != ""):
        if not participant_data_folder.exists():
            print("WARNING: Unable to find deidentified BIDS data folder for \"" + data_file + "\".")
            issues_during_upload = True
            continue
                                                        
            
    # upload sourcedata
    if sourcedata_upload_enabled:
        folder_id = box.create_folder(settings_box["sourcedata_dir_id"],(participant_study_id, participant_session_id))
        if folder_id==-1:
            print("WARNING: Unable to create source data folder on Box for " + participant_study_id + ", " + participant_session_id + ".")
            issues_during_upload = True
            continue

        data_file_srcpath = session_dir.joinpath(data_file)
        summary_file_srcpath = session_dir.joinpath(session["summary_file"])

        if data_file_srcpath.exists():
            res = box.upload_file(str(data_file_srcpath), folder_id)
            if res==-1:
                print("WARNING: Unable to upload source data to Box for " + participant_study_id + ", " + participant_session_id + ".")
                issues_during_upload = True
                continue

        if summary_file_srcpath.exists():
            res = box.upload_file(str(summary_file_srcpath), folder_id)
            if res==-1:
                print("WARNING: Unable to upload summary file to Box for " + participant_study_id + ", " + participant_session_id + ".")
                issues_during_upload = True
                continue
    
    # upload BIDS data
    if data_upload_enabled:
        session_folder_id = box.create_folder(settings_box["data_dir_id"],(participant_study_id, participant_session_id))
        if session_folder_id==-1:
            print("WARNING: Unable to create data folder on Box for " + participant_study_id + ", " + participant_session_id + ".")
            issues_during_upload = True
            continue

        session_srcdir = participant_data_folder.joinpath(participant_session_id)
        if session_srcdir.exists():
            upload_interrupted = False
            for dirpath, dirnames, filenames in os.walk(session_srcdir):

                # get relative path of current folder
                dirpath_stem = dirpath.removeprefix(str(session_srcdir))
                if len(dirpath_stem) == 0:
                    current_folder_id = session_folder_id
                else:
                    dirpath_stem_parts = dirpath_stem.strip().removeprefix("/").removeprefix("\\").replace("\\","/").split("/")
                    current_folder_id = box.create_folder(session_folder_id,dirpath_stem_parts)
                    if current_folder_id == -1:
                        print("WARNING: Unable to create all folders on Box for " + participant_study_id + ", " + participant_session_id + ".")
                        upload_interrupted = True
                        break

                # create all subfolders
                for dirname in dirnames:
                    subfolder_id = box.create_folder(current_folder_id,(dirname, ))
                    if subfolder_id == -1:
                        print("WARNING: Unable to create all folders on Box for " + participant_study_id + ", " + participant_session_id + ".")
                        upload_interrupted = True
                        break
                if upload_interrupted:
                    break

                # upload all files in current folder
                for filename in filenames:
                    file_srcpath = Path(dirpath).joinpath(filename)
                    res = box.upload_file(str(file_srcpath), current_folder_id)
                    if res==-1:
                        print("WARNING: Unable to upload all files to Box for " + participant_study_id + ", " + participant_session_id + ".")
                        upload_interrupted = True
                        break
                if upload_interrupted:
                    break
            
            # check for any errors
            if upload_interrupted:
                issues_during_upload = True
                continue

    # upload deidentified BIDS data
    if deidentified_data_upload_enabled and settings_study["deidentify_data"] and (participant_deidentified_id != None) and (participant_deidentified_id != ""):
        session_folder_id = box.create_folder(settings_box["deidentified_data_dir_id"],(participant_deidentified_id, participant_session_id))
        if session_folder_id==-1:
            print("WARNING: Unable to create deidentified data folder on Box for " + participant_deidentified_id + ", " + participant_session_id + ".")
            issues_during_upload = True
            continue

        session_srcdir = participant_deidentified_data_folder.joinpath(participant_session_id)
        if session_srcdir.exists():
            upload_interrupted = False
            for dirpath, dirnames, filenames in os.walk(session_srcdir):

                # get relative path of current folder
                dirpath_stem = dirpath.removeprefix(str(session_srcdir))
                if len(dirpath_stem) == 0:
                    current_folder_id = session_folder_id
                else:
                    dirpath_stem_parts = dirpath_stem.strip().removeprefix("/").removeprefix("\\").replace("\\","/").split("/")
                    current_folder_id = box.create_folder(session_folder_id,dirpath_stem_parts)
                    if current_folder_id == -1:
                        print("WARNING: Unable to create all folders on Box for " + participant_deidentified_id + ", " + participant_session_id + ".")
                        upload_interrupted = True
                        break

                # create all subfolders
                for dirname in dirnames:
                    subfolder_id = box.create_folder(current_folder_id,(dirname, ))
                    if subfolder_id == -1:
                        print("WARNING: Unable to create all folders on Box for " + participant_deidentified_id + ", " + participant_session_id + ".")
                        upload_interrupted = True
                        break
                if upload_interrupted:
                    break

                # upload all files in current folder
                for filename in filenames:
                    file_srcpath = Path(dirpath).joinpath(filename)
                    res = box.upload_file(str(file_srcpath), current_folder_id)
                    if res==-1:
                        print("WARNING: Unable to upload all files to Box for " + participant_deidentified_id + ", " + participant_session_id + ".")
                        upload_interrupted = True
                        break
                if upload_interrupted:
                    break
            
            # check for any errors
            if upload_interrupted:
                issues_during_upload = True
                continue
                
    # update session
    db.update_mri_session(session_id, data_uploaded_dt=datetime.now().timestamp())

    db.commit()

# close connection to database
db.close()

# close log file
print("Upload data complete")
close_log_file()

# send notification if there were any issues with the upload
if mail_settings["errors"]["send_notification"] and issues_during_upload:
        notifications.send_email(mail_settings["errors"]["subject"],
                         "Errors encountered when uploading data to Box. Please check the attached log file for more information.", 
                         mail_settings["errors"]["recipients"],
                         mail_settings["mail_server"]["address"],
                         mail_settings["mail_server"]["port"],
                         mail_settings["mail_server"]["user"],
                         mail_settings["mail_server"]["password"],
                         (log_file_name, ))

