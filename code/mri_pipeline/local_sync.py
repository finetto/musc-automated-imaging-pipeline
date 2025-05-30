from pathlib import Path
import os
import sys
from datetime import datetime

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
rootdir = os.path.dirname(parentdir)

sys.path.insert(0, parentdir) 
from common import local_sync_settings, processing_settings
from common import database, database_settings
from common import notifications, notification_settings
from common import cbi_parse
from common import study, study_settings

# global variables
log_file_name = os.path.join(rootdir,"log","cbi_sync_log.txt")
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
    print("------- LOCAL SYNC -------")
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
    if settings_notification["errors"]["send_notification"]:
        notifications.send_email(settings_notification["errors"]["subject"],
                         "Attention: Errors were encountered during the execution of 'local_sync.py'\nPlease check the attached log file for further information.", 
                         settings_notification["errors"]["recipients"],
                         settings_notification["mail_server"]["address"],
                         settings_notification["mail_server"]["port"],
                         settings_notification["mail_server"]["user"],
                         settings_notification["mail_server"]["password"],
                         (log_file_name, ))

    sys.exit()

# open log file
open_log_file()

# get notification settings from file
mail_settings_file = os.path.join(rootdir,"settings","notification_settings.json")
settings_notification = notification_settings.load_from_file(mail_settings_file)
if settings_notification == -1:
    print("ERROR: Unable to load notification settings from \"" + mail_settings_file + "\".")
    terminate_after_error()

# get local sync settings from file
local_sync_settings_file = os.path.join(rootdir,"settings","local_sync_settings.json")
settings_local_sync = local_sync_settings.load_from_file(local_sync_settings_file)
if settings_local_sync == -1:
    print("ERROR: Unable to load local sync settings settings from \"" + local_sync_settings_file + "\".")
    terminate_after_error()

# check if local sync is enabled
if not settings_local_sync["use_local_sync"]:
    print("\nLocal sync disabled.\nTerminating script.")
    close_log_file()
    sys.exit()

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
settings_db = database_settings.load_from_file(db_settings_file)
if settings_db == -1:
    print("ERROR: Unable to load database settings from \"" + db_settings_file + "\".")
    terminate_after_error()

# get available sessions from local folder
#cbi_data = cbi_query.get_sessions(settings_cbi["connection"]["host"], 
#                                  settings_cbi["remote_data_dir"], 
#                                  settings_cbi["connection"]["credentials_file"])
#if cbi_data == -1: terminate_after_error()
# TODO: get local data
local_data = -1


# connect to database
db = database.db(settings_db["db_path"])
db.n_default_query_attempts = settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

# process all session data files
for data_file in local_data["data_files"]:

    # check if this session is already in database
    session_id = db.get_mri_session_id(data_file=data_file)
    if session_id == -1: terminate_after_error()
    if session_id is not None: continue

    # get session info
    session_info = cbi_parse.get_timestamp_and_description(data_file)
    if session_info == -1:
        print("WARNING: File \"" + data_file + "\" will be skipped.")
        continue

    print("New session data found: \"" + session_info["name"] + "\"")
    

    # get participant study ID  and session ID from description
    participant_info = cbi_parse.get_subject_and_session(session_info, settings_study["subject_identifier_format"], 
                                                         settings_study["session_identifier_format"])
    if participant_info == -1:
        print("WARNING: File \"" + data_file + "\" will be skipped.")
        continue

    # check if we found a subject ID
    participant_id = None
    if participant_info["subject_id"]:
        # look for subject in database
        participant_id = db.get_participant_id(study_id=participant_info["subject_id"])
        if participant_id == -1: terminate_after_error()
        if participant_id is None: # participant not in database -> add and get new ID

            # get all current deidentified IDs
            deidentified_ids = []
            all_participant_data = db.get_all_participant_data()
            for participant in all_participant_data:
                deidentified_ids.append(participant["deidentified_id"])
            deidentified_ids = tuple(deidentified_ids)

            new_deidentified_id = study.generate_deidentified_id(used_ids=deidentified_ids, 
                                                                 prefix=settings_study["deidentified_subject_identifier_format"]["desired_prefix"]+settings_study["deidentified_subject_identifier_format"]["desired_start_str"],
                                                                 digits=settings_study["deidentified_subject_identifier_format"]["desired_digits"])
            

            participant_id = db.add_participant(study_id=participant_info["subject_id"], 
                                                deidentified_id=new_deidentified_id,
                                                group_assignment="patient")
            
            if participant_id == -1: terminate_after_error()

            print("New participant found: " + participant_info["subject_id"])

    # add row to session table
    session_id = db.add_mri_session(participant_id = participant_id,
                                participant_session_id = participant_info["session_id"],
                                data_file = data_file,
                                description = session_info["description"],
                                data_recorded_date = session_info["date"],
                                data_recorded_time = session_info["time"],
                                data_recorded_dt = session_info["datetime"].timestamp())#,
                                #data_downloaded_dt = datetime.now().timestamp())    # only needed for debugging with data that was already downloaded
    if session_id == -1: terminate_after_error()

# commit changes
db.commit()

# look for MRI sessions with missing summary files and find new matches
sessions_with_missing_summary = db.find_mri_sessions_with_missing_summary(exclude_skipped=True)
if sessions_with_missing_summary == -1: terminate_after_error()
for session in sessions_with_missing_summary:
    # extract data from query
    session_id = session["id"]
    data_file = session["data_file"]
    data_recorded_date = session["data_recorded_date"]
    data_recorded_time = session["data_recorded_time"]
    session_name = Path(data_file).stem
    found_by_date = False

    # look for summary files matching this session name
    matching_summary_file = None
    if (session_name != None) and (session_name != ""):
        for summary_file in local_data["summary_files"]:
            if session_name in summary_file:
                matching_summary_file = summary_file
                break

    # if not found, look for summary files containing the matching date and time
    if (not matching_summary_file) and (data_recorded_date != None) and (data_recorded_date != "") and (data_recorded_time != None) and (data_recorded_time != ""):
        dt_search_str = "_" + data_recorded_date.replace("/","") + "_" + data_recorded_time.replace(":","") + "_"

        for summary_file in local_data["summary_files"]:
            if dt_search_str in summary_file:
                matching_summary_file = summary_file
                found_by_date = True
                break

    # store result in database
    if matching_summary_file:
        res = db.update_mri_session(session_id, 
                                summary_file=matching_summary_file)
        if res == -1: terminate_after_error()
        print("Found summary file for " + session_name + ": " + matching_summary_file)
        if found_by_date:
            print("   Note: summary file found by date and time, but session name does not match.")

# commit changes
db.commit()


# copy missing data files
sessions_requiring_data_download = db.find_mri_sessions_requiring_data_download(exclude_skipped=True)
if sessions_requiring_data_download == -1: terminate_after_error()
for session in sessions_requiring_data_download:
    # extract data from query
    session_id = session["id"]
    data_file = session["data_file"]

    # get folder for session
    session_name = Path(data_file).stem
    session_dir = Path(settings_processing["mri"]["workdir"]).joinpath(session_name)
    if not session_dir.exists():
        os.mkdir(session_dir)

    # copy file
    print("Copying \"" + data_file + "\"")
    #success = cbi_query.download_file(data_file, 
    #                                  settings_cbi["connection"]["host"], 
    #                                  settings_cbi["remote_data_dir"], 
    #                                  settings_cbi["connection"]["credentials_file"], 
    #                                  session_dir,
    #                                  show_progress=False)
    # TODO: copy file to work directory
    success = 1

    # update database
    if success == 1:
        res = db.update_mri_session(session_id, 
                                data_downloaded_dt=datetime.now().timestamp())
        if res == -1: terminate_after_error()
        
        # commit changes immediately since this part can take some time
        db.commit()


# copy missing summary files
sessions_requiring_summary_download = db.find_mri_sessions_requiring_summary_download(exclude_skipped=True)
if sessions_requiring_summary_download == -1: terminate_after_error()
for session in sessions_requiring_summary_download:
    # extract data from query
    session_id = session["id"]
    data_file = session["data_file"]
    summary_file = session["summary_file"]

    # get folder for session
    session_name = Path(data_file).stem
    session_dir = Path(settings_processing["mri"]["workdir"]).joinpath(session_name)
    if not session_dir.exists():
        os.mkdir(session_dir)

    # download file
    print("Copying \"" + summary_file + "\"")
    #success = cbi_query.download_file(summary_file, 
    #                                  settings_cbi["connection"]["host"], 
    #                                  settings_cbi["remote_data_dir"], 
    #                                  settings_cbi["connection"]["credentials_file"], 
    #                                  session_dir,
    #                                  show_progress=False)
    # TODO: copy file to work directory
    success = 1

    # update database
    if success == 1:
        res = db.update_mri_session(session_id, 
                                summary_downloaded_dt=datetime.now().timestamp())
        if res == -1: terminate_after_error()

        # commit changes immediately
        db.commit()

# close connection to database
db.close()

# close log file
print("Sync complete")
close_log_file()
