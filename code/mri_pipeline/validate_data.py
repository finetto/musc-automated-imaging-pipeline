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
log_file_name = os.path.join(rootdir,"log","validate_data_log.txt")
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
                         "Attention: Errors were encountered during the execution of 'validate_data.py'\nPlease check the attached log file for further information.", 
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

# find sessions for which data is available and extracted but not yet validated
# skip sessions that should be skipped
sessions_requiring_validation = db.find_mri_sessions_requiring_data_validation(exclude_skipped=True)
if sessions_requiring_validation == -1: terminate_after_error()

send_validation_error_notification = False
validation_error_notification = "Attention: Errors were encountered while validating the downloaded session data.\nPlease check the attached log file for further details.\n\n"

for session in sessions_requiring_validation:
    session_id = session["id"]
    participant_id = session["participant_id"]
    data_file = session["data_file"]

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

    # get conversion folder
    convert_folder = session_dir.joinpath("convert")
    if not convert_folder.exists():
        print("ERROR: Unable to find converted data folder for \"" + data_file + "\".")
        terminate_after_error()

    # get nifti folder - make sure previous conversion results are removed
    nifti_folder = convert_folder.joinpath("nifti")
    if not convert_folder.exists():
        print("ERROR: Unable to find nifti data folder for \"" + data_file + "\".")
        terminate_after_error()

    # get log folder
    log_folder = convert_folder.joinpath("log")
    if not log_folder.exists():
        print("ERROR: Unable to find conversion log folder for \"" + data_file + "\".")
        terminate_after_error()

    # get conversion log file
    dcm2niix_log_file = log_folder.joinpath("dcm2niix_log.txt")
    if not dcm2niix_log_file.exists():
        print("ERROR: Unable to find dcm2niix log file for \"" + data_file + "\".")
        terminate_after_error()

    # parse dcm2niix log file
    conversion_summary = mri_proc_utils.parse_dcm2niix_log(str(dcm2niix_log_file))
    if conversion_summary==-1:
        print("ERROR: Unable to parse dcm2niix log file for \"" + data_file + "\".")
        terminate_after_error()

    # validate converted files
    converted_series = []
    errors = []
    max_series = max(conversion_summary, key=lambda conversion_info:conversion_info["series_number"])["series_number"]

    for series_number in range(1,max_series+1):

        validated_series_files = True

        # find matches
        matching_conversion_info = list(filter(lambda conversion_info:conversion_info["series_number"]==series_number, conversion_summary))
        matching_series = db.get_mri_series_data(session_id=session_id, series_number=series_number, return_only_first=True)

        # sort conversion info by file name (in series with multiple converted files, they are sometimes out of order after conversion)
        matching_conversion_info = sorted(matching_conversion_info, key=lambda x: x['file'])

        #initialize errors
        errors_i = ""

        # make sure we found at least one matching converted file
        if len(matching_conversion_info)<1:
            errors.append({"series_number": series_number,
                        "message": "No matching series found in converted files."})
            continue

        # make sure we found at least one matching series in database
        if (matching_series)==None or (matching_series==-1):
            errors.append({"series_number": series_number,
                        "message": "No matching series found in database."})
            continue

        # get number of converted files
        number_files_converted = 0
        for conversion_info in matching_conversion_info:
            number_files_converted = number_files_converted+conversion_info["number_files"]

        # make sure all converted files exist  
        all_files_found = True
        for conversion_info in matching_conversion_info:
            nifti_file = nifti_folder.joinpath(str(series_number).zfill(3)).joinpath(conversion_info["file"] + ".nii.gz")
            sidecar_file = nifti_folder.joinpath(str(series_number).zfill(3)).joinpath(conversion_info["file"] + ".json")

            if (not nifti_file.exists()) or (not sidecar_file.exists()):
                print(nifti_file)
                print(sidecar_file)
                all_files_found = False
        
        if not all_files_found:
            errors.append({"series_number": series_number,
                        "message": "Could not find all converted files."})
            validated_series_files = False

        # add to validated series array
        converted_series.append({
            "series_id": matching_series["id"],
            "series_number": series_number,
            "series_description": matching_series["description"],
            "number_files": number_files_converted,
            "conversion_info": matching_conversion_info,
            "validated_files": validated_series_files,
            "dcm2bids_criteria": None,
            "dcm2bids_criteria_in_config": None,
            "duplicate_series": [],
            "skip_series": not validated_series_files
        })

    # check for errors
    if len(errors)>0:
        send_validation_error_notification = True
        print("WARNING: Errors found when matching recorded files to converted files for session\"" + session_name + "\":")
        validation_error_notification = validation_error_notification + "Errors found when matching recorded files to converted files for session\"" + session_name + "\":\n"
        for error in errors:
            print(" - series " + str(error["series_number"]) + ": " + error["message"])
            validation_error_notification = validation_error_notification + " - series " + str(error["series_number"]) + ": " + error["message"] + "\n"
        validation_error_notification = validation_error_notification + "\n\n"

    # make sure all series have a match
    if len(converted_series) != max_series:
        send_validation_error_notification = True
        print("WARNING: Could not find matching files for some series in session \"" + session_name + "\".")
        validation_error_notification = validation_error_notification + "Could not find matching files for some series in session \"" + session_name + "\".\n\n"

    # parse sidecar files and extract dcm2bids search criteria
    all_dcm2bids_search_criteria_values = []
    for index, series in enumerate(converted_series):

        # skip series that are not validated
        if not series["validated_files"]:
            continue

        # initialize dcm2bids search criteria
        dcm2bids_search_criteria = dict()
        dcm2bids_search_criteria_values = []
        series_description = None

        # loop through converted files for this series and update dcm2bids search criteria
        # when there are multiple converted files for one series, they share the same search criteria
        # for now, we just loop through them all and overwrite until we hit the last iteration
        # TODO: when there are multiple converted files, we could consider using the largest (lexographically or numerically) values instead of the last ones
        #       since the converted files are sorted by file name, this should already be happening in most situations
        for conversion_info in series["conversion_info"]:
            dcm2bids_search_criteria = dict()
            dcm2bids_search_criteria_values = []
            series_description = None

            series_number = conversion_info["series_number"]
            sidecar_file = nifti_folder.joinpath(str(series_number).zfill(3)).joinpath(conversion_info["file"] + ".json")
            
            try:
                with open(str(sidecar_file), 'r') as f:
                    info = json.load(f)
            except Exception as e:
                print("ERROR: Unable to read sidecar file \"" + str(sidecar_file) + "\":\n")
                print(e)
                terminate_after_error()

            for key in config_dcm2bids["search_criteria"]["keys"]:
                if key in info:
                    dcm2bids_search_criteria[key] = info[key]
                    dcm2bids_search_criteria_values.append(info[key])
                else:
                    dcm2bids_search_criteria_values.append(None)

            # extract series description
            if "SeriesDescription" in info:
                series_description = info["SeriesDescription"]


        converted_series[index]["dcm2bids_criteria"] = dcm2bids_search_criteria
        converted_series[index]["dcm2bids_criteria_in_config"] =  dcm2bids_search_criteria in config_dcm2bids["search_criteria"]["criteria"]

        if series_description != None:
            converted_series[index]["series_description"] = series_description

        all_dcm2bids_search_criteria_values.append(dcm2bids_search_criteria_values)

        # if search critera don't match any criteria in the dcm2bids config, flag the series to be skipped
        if not converted_series[index]["dcm2bids_criteria_in_config"]:
            converted_series[index]["skip_series"] = True

    # find unique dcm2bids search criteria values
    unique_dcm2bids_search_criteria_values = []
    for dcm2bids_search_criteria_values in all_dcm2bids_search_criteria_values:
        if not dcm2bids_search_criteria_values in unique_dcm2bids_search_criteria_values:
            unique_dcm2bids_search_criteria_values.append(dcm2bids_search_criteria_values)

    # get potential duplicate series, then flag all duplicates to be skipped except the last series
    for dcm2bids_search_criteria_values in unique_dcm2bids_search_criteria_values:
        matches_idx = []
        matches_series_n = []
        for index, series_dcm2bids_search_criteria_values in enumerate(all_dcm2bids_search_criteria_values):
            if dcm2bids_search_criteria_values == series_dcm2bids_search_criteria_values:
                matches_idx.append(index)
                matches_series_n.append(converted_series[index]["series_number"])

        # add information on duplicates to corresponding series
        # flag all to be skipped except the last series (with highest series number)
        if len(matches_idx)>1:
            for index in matches_idx:
                converted_series[index]["duplicate_series"] = matches_series_n
                if converted_series[index]["series_number"] != max(matches_series_n):
                    converted_series[index]["skip_series"] = True

    # write to database
    all_converted_files_valid = True
    any_converted_files_valid = False
    for series in converted_series:

        # convert some fields to json strings
        dcm2bids_criteria = None
        if (series["dcm2bids_criteria"] != None) and (len(series["dcm2bids_criteria"]) > 0):
            dcm2bids_criteria = json.dumps(series["dcm2bids_criteria"])

        duplicate_series = None
        if (series["duplicate_series"] != None) and (len(series["duplicate_series"]) > 0):
            duplicate_series = json.dumps(series["duplicate_series"])

        db.update_mri_series(id = series["series_id"],
                             description = series["series_description"],
                             number_files = series["number_files"],
                             files_validated_dt = datetime.now().timestamp(),
                             files_valid = series["validated_files"],
                             dcm2bids_criteria = dcm2bids_criteria,
                             dcm2bids_criteria_in_config = series["dcm2bids_criteria_in_config"],
                             duplicate_series = duplicate_series,
                             skip_processing = series["skip_series"])
        
        all_converted_files_valid = all_converted_files_valid and series["validated_files"]
        any_converted_files_valid = any_converted_files_valid or series["validated_files"]
        
    db.update_mri_session(id=session_id, 
                          conversion_validated_dt=datetime.now().timestamp(),
                          conversion_valid=all_converted_files_valid)
    db.commit()

# close connection to database
db.close()

# close log file
print("Validate data complete")
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