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
log_file_name = os.path.join(rootdir,"log","validate_data_with_summary_log.txt")
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
    print("----- VALIDATE DATA ------")
    print("------ WITH SUMMARY ------")
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
                         "Attention: Errors were encountered during the execution of 'validate_data_with_summary.py'\nPlease check the attached log file for further information.", 
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

# find sessions for which data is available and extracted and validated, but not validated with summary
# skip sessions that should be skipped
sessions_requiring_validation = db.find_mri_sessions_requiring_data_validation_with_summary(exclude_skipped=True)
if sessions_requiring_validation == -1: terminate_after_error()

send_validation_error_notification = False
validation_error_notification = "Attention: Errors were encountered while validating the downloaded session data.\nPlease check the attached log file for further details.\n\n"

for session in sessions_requiring_validation:
    session_id = session["id"]
    participant_id = session["participant_id"]
    data_file = session["data_file"]
    summary_file = session["summary_file"]
    data_recorded_dt = session["data_recorded_dt"]
    summary_downloaded_dt = session["summary_downloaded_dt"]
    conversion_valid = session["conversion_valid"]

    # get all series for this session
    session_series = db.get_mri_series_data(session_id=session_id)
    if len(session_series) < 1:
        print("ERROR: No series found in database for \"" + data_file + "\".")
        terminate_after_error()

    # get folder for session
    session_name = Path(data_file).stem
    session_dir = Path(settings_processing["mri"]["workdir"]).joinpath(session_name)
    if not session_dir.exists():
        print("ERROR: Unable to find data folder for \"" + data_file + "\".")
        terminate_after_error()

    # check if summary file was downloaded
    if (summary_downloaded_dt == None) or (summary_file == None) or (summary_file == ""):

        # check if we have timed out on wait for summary file
        delta = datetime.now()-datetime.fromtimestamp(data_recorded_dt)
        delta_hours = delta.total_seconds() / 3600

        if delta_hours > settings_processing["mri"]["summary_file_wait_timeout_h"]:
            
            # stop waiting and mark this session as validated
            db.update_mri_session(id = session_id, 
                                  conversion_validated_with_summary_dt = datetime.now().timestamp())
            db.commit()

            # queue notification
            send_validation_error_notification = True
            print("WARNING: Waited for more than " + str(settings_processing["mri"]["summary_file_wait_timeout_h"]) + " hours for summary file of session \"" + session_name + "\".\nThis session will be marked as validated and will be processed without the summary file.\n\n")
            validation_error_notification = validation_error_notification + "Waited for more than " + str(settings_processing["mri"]["summary_file_wait_timeout_h"]) + " hours for summary file of session \"" + session_name + "\".\nThis session will be marked as validated and will be processed without the summary file.\n\n"

        continue

    # get summary file path
    summary_file_path = session_dir.joinpath(summary_file)
    if not summary_file_path.exists():
        print("ERROR: Unable to find summary file for \"" + data_file + "\".")
        terminate_after_error()

    # parse session summary
    session_summary = mri_proc_utils.parse_summary_file(str(session_dir.joinpath(summary_file)))
    if session_summary==-1:
        print("ERROR: Unable to parse summary file for \"" + data_file + "\".")
        terminate_after_error()

    # validate each series by looking at summary file and database entries
    converted_series = []
    errors = []
    max_series_in_summary = max(session_summary["series_info"], key=lambda series_info:series_info["series_number"])["series_number"]
    max_series_in_db = max(session_series, key=lambda series_info:series_info["series_number"])["series_number"]
    max_series = max(max_series_in_summary, max_series_in_db)
    
    number_files_in_db_total = 0
    all_series_valid = True
    any_series_valid = False

    for series_number in range(1,max_series+1):

        # find matches
        matching_series_info = list(filter(lambda series_info:series_info["series_number"]==series_number, session_summary["series_info"]))
        matching_series = db.get_mri_series_data(session_id=session_id, series_number=series_number, return_only_first=True)

        #initialize errors
        errors_i = ""

        # make sure we found at least one matching series in database
        if (matching_series)==None or (matching_series==-1):
            errors.append({"series_number": series_number,
                        "message": "No matching series found in database."})
            continue

        # get series validation flag
        validated_series_files = True
        files_valid = matching_series["files_valid"]
        skip_processing = matching_series["skip_processing"]

        # there should be at least one matching series in summary file
        if len(matching_series_info)<1:
            errors.append({"series_number": series_number,
                        "message": "No matching series found in summary file."})
            validated_series_files = False

        # there should only be one matching series in summary file
        if len(matching_series_info)>1:
            errors.append({"series_number": series_number,
                        "message": "More than one matching series found in summary file."})
            validated_series_files = False

        # get recording datetime and number of recorded files from summary
        if len(matching_series_info) > 0:
            matching_series_info = matching_series_info[0]
            number_files_recorded = matching_series_info["number_files"]
            series_recorded_dt = matching_series_info["datetime"].timestamp()
        else:
            series_recorded_dt = None
            number_files_recorded = 0

        # get number of files in db for this series
        number_files_in_db = matching_series["number_files"]

        # update total number of files in session
        number_files_in_db_total = number_files_in_db_total+number_files_in_db

        # make sure all recorded files were converted
        if number_files_recorded != number_files_in_db:
            errors.append({"series_number": series_number,
                        "message": "Number of recorded files does not match number of files in database."})
            validated_series_files = False

        # update series validation flags
        if not validated_series_files:
            files_valid = False
            skip_processing = True
        all_series_valid = all_series_valid and validated_series_files
        any_series_valid = any_series_valid or validated_series_files

        # update series in db
        db.update_mri_series(id = matching_series["id"],
                             series_recorded_dt=series_recorded_dt,
                             files_validated_with_summary_dt = datetime.now().timestamp(),
                             files_valid = files_valid,
                             skip_processing = skip_processing)
        db.commit()

    # check for errors
    if len(errors)>0:
        send_validation_error_notification = True
        print("WARNING: Errors found when validating session\"" + session_name + "\" with session summary file:")
        validation_error_notification = validation_error_notification + " Errors found when validating session\"" + session_name + "\" with session summary file:\n"
        for error in errors:
            print(" - series " + str(error["series_number"]) + ": " + error["message"])
            validation_error_notification = validation_error_notification + " - series " + str(error["series_number"]) + ": " + error["message"] + "\n"
        validation_error_notification = validation_error_notification + "\n\n"

    # compare total number of files
    if session_summary["session_info"]["total_files"] != number_files_in_db_total:
        print("WARNING: Total number of files in session summary does not match number of converted DICOM files for session \"" + session_name + "\"")
        send_validation_error_notification = True
        validation_error_notification = validation_error_notification + "Total number of files in session summary does not match number of converted DICOM files for session \"" + session_name + "\".\n\n"

    # update conversion valid flag for session
    if not all_series_valid:
        conversion_valid = False

    # update session
    db.update_mri_session(id=session_id, 
                          conversion_validated_with_summary_dt=datetime.now().timestamp(),
                          conversion_valid=conversion_valid)
    db.commit()

# close connection to database
db.close()

# close log file
print("Validate data with summary complete")
close_log_file()

# send error notification
if mail_settings["errors"]["send_notification"] and send_validation_error_notification:
        notifications.send_email(mail_settings["errors"]["subject"],
                         validation_error_notification, 
                         mail_settings["errors"]["recipients"],
                         mail_settings["mail_server"]["address"],
                         mail_settings["mail_server"]["port"],
                         mail_settings["mail_server"]["user"],
                         mail_settings["mail_server"]["password"],
                         (log_file_name, ))