from pathlib import Path
import os
import sys
from datetime import datetime

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
rootdir = os.path.dirname(parentdir)

sys.path.insert(0, parentdir) 
from common import database, database_settings
from common import notifications, notification_settings

# global variables
log_file_name = os.path.join(rootdir,"log","send_validation_notifications_log.txt")
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
    print("--- SEND NOTIFICATIONS ---")
    print("----------- FOR ----------")
    print("----- DATA VALIDATION ----")
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
                         "Attention: Errors were encountered during the execution of 'send_validation_notifications.py'\nPlease check the attached log file for further information.", 
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

# get database settings from file
db_settings_file = os.path.join(rootdir,"settings","database_settings.json")
db_settings = database_settings.load_from_file(db_settings_file)
if db_settings == -1:
    print("ERROR: Unable to load database settings from \"" + db_settings_file + "\".")
    terminate_after_error()

# check if notifications are enabled
if not settings_notification["mri_data_validation"]["send_notification"]:
    print("Notifications disabled.")
    close_log_file()
    sys.exit()

# connect to database
db = database.db(db_settings["db_path"])
db.n_default_query_attempts = db_settings["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

# initialize list of sessions that will receive a new notification
sessions_receiving_notification = []

# find all sessions for which no notification has been sent
n_first_notifications = 0
first_notification_text = ""

sessions_requiring_first_notification = db.find_mri_sessions_requiring_first_notification()
if sessions_requiring_first_notification == -1: terminate_after_error()

for session in sessions_requiring_first_notification:
    session_id = session["id"]
    session_description = session["description"]
    session_date = session["data_recorded_date"]
    session_time = session["data_recorded_time"]

    # get duplicate series in session (if any)
    duplicate_series = db.find_duplicate_series_in_session(session_id=session_id)
    if duplicate_series == -1: terminate_after_error()

    description = "\t- " + session_date + " " + session_time + " | " + session_description

    if (duplicate_series != None) and len(duplicate_series)>0:
        description = description + "\n\n\t  ATTENTION: duplicate series found in this session. By default, the last series is processed and previous ones are skipped. Please review.\n"

    n_first_notifications = n_first_notifications+1
    first_notification_text = first_notification_text + description + "\n"

    sessions_receiving_notification.append(session)

if n_first_notifications == 1:
    first_notification_text = "One new session was downloaded from CBI Home. Please validate subject ID and session ID:\n" + first_notification_text
elif n_first_notifications > 1:
    first_notification_text = str(n_first_notifications) + " new sessions were downloaded from CBI Home. Please validate subject IDs and session IDs:\n" + first_notification_text



# find all sessions for which a notification has been sent, but that have not been validated yet
n_reminder_notifications = 0
reminder_notification_text = ""

if settings_notification["mri_data_validation"]["send_reminder"] and (settings_notification["mri_data_validation"]["reminder_interval_h"] > 0):

    sessions_requiring_reminder_notification = db.find_mri_sessions_requiring_reminder_notification()
    if sessions_requiring_reminder_notification == -1: terminate_after_error()

    for session in sessions_requiring_reminder_notification:
        session_id = session["id"]
        session_description = session["description"]
        session_date = session["data_recorded_date"]
        session_time = session["data_recorded_time"]
        notification_sent_dt = session["notification_sent_dt"]

        # get duplicate series in session (if any)
        duplicate_series = db.find_duplicate_series_in_session(session_id=session_id)
        if duplicate_series == -1: terminate_after_error()

        # calculate time since last notification
        last_notification_dt = datetime.fromtimestamp(notification_sent_dt)
        delta = datetime.now()-last_notification_dt
        delta_hours = delta.total_seconds() / 3600

        # skip if less than [reminder_interval_h] hours have passed since last notification
        if delta_hours < settings_notification["mri_data_validation"]["reminder_interval_h"]: continue

        description = "\t- " + session_date + " " + session_time + " | " + session_description

        if (duplicate_series != None) and len(duplicate_series)>0:
            description = description + "\n\n\t  ATTENTION: duplicate series found in this session. By default, the last series is processed and previous ones are skipped. Please review.\n"

        n_reminder_notifications = n_reminder_notifications+1
        reminder_notification_text = reminder_notification_text + description + "\n"

        sessions_receiving_notification.append(session)

    if n_reminder_notifications == 1:
        reminder_notification_text = "One session has been in queue for validation for more than " + str(settings_notification["mri_data_validation"]["reminder_interval_h"]) + " hours. Please validate subject ID and session ID:\n" + reminder_notification_text
    elif n_reminder_notifications > 1:
        reminder_notification_text = str(n_reminder_notifications) + " sessions have been in queue for validation for more than " + str(settings_notification["mri_data_validation"]["reminder_interval_h"]) + " hours. Please validate subject IDs and session IDs:\n" + reminder_notification_text

# compile full notification
full_notification_text = ""
notification_necessary = False
if (n_first_notifications>0) and (n_reminder_notifications>0):
    full_notification_text = first_notification_text + "\n\n" + reminder_notification_text
    notification_necessary = True
elif n_first_notifications>0:
    full_notification_text = first_notification_text
    notification_necessary = True
elif n_reminder_notifications>0:
    full_notification_text = reminder_notification_text
    notification_necessary = True


# send notification
if notification_necessary:
    notifications.send_email(settings_notification["mri_data_validation"]["subject"],
                        full_notification_text, 
                        settings_notification["mri_data_validation"]["recipients"],
                        settings_notification["mail_server"]["address"],
                        settings_notification["mail_server"]["port"],
                        settings_notification["mail_server"]["user"],
                        settings_notification["mail_server"]["password"])
    
    # Update DB by setting the notification time
    notification_sent_dt = datetime.now().timestamp()

    for session in sessions_receiving_notification:
        session_id = session["id"]

        res = db.update_mri_session(session_id, notification_sent_dt=notification_sent_dt)
        if res == -1: terminate_after_error()
    db.commit()

    print("Notifications sent:\n")
    print(full_notification_text + "\n")

else:
    print("No notifications necessary.")

# close connection to database
db.close()

# close log file
print("Notifications complete")
close_log_file()