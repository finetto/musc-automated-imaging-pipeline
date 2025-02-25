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

# define exit after error function
def terminate_after_error():

    print("\nTerminating script.")

    # send notification
    if mail_settings["errors"]["send_notification"]:
        notifications.send_email(mail_settings["errors"]["subject"],
                         "Attention: Errors were encountered during the execution of 'backup_configuration.py'.", 
                         mail_settings["errors"]["recipients"],
                         mail_settings["mail_server"]["address"],
                         mail_settings["mail_server"]["port"],
                         mail_settings["mail_server"]["user"],
                         mail_settings["mail_server"]["password"])

    sys.exit()

# get notification settings from file
mail_settings_file = os.path.join(rootdir,"settings","notification_settings.json")
mail_settings = notification_settings.load_from_file(mail_settings_file)
if mail_settings == -1:
    print("ERROR: Unable to load notification settings from \"" + mail_settings_file + "\".")
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
    sys.exit()

# check if backup folder was specified
if (settings_box["app_backup_dir_id"] == None) or (settings_box["app_backup_dir_id"] == ""):
    backup_enabled = False
else:
    backup_enabled = True

if not backup_enabled:
    print("\nBox backup disabled.\nTerminating script.")
    sys.exit()

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

# check existence of backup folder
if backup_enabled and (not box.folder_exists(settings_box["app_backup_dir_id"])):
    print("ERROR: Backup folder does not exist on Box.")
    terminate_after_error()


issues_during_upload = False

# backup database
folder_id = box.create_folder(settings_box["app_backup_dir_id"],("database", ))
if folder_id==-1:
    print("WARNING: Unable to create database folder on Box.")
    issues_during_upload = True
else:
    database_file_srcpath = Path(db_settings["db_path"])

    if database_file_srcpath.exists():
        res = box.upload_file(str(database_file_srcpath), folder_id)
        if res==-1:
            print("WARNING: Unable to backup database to Box.")
            issues_during_upload = True
            

# backup settings
folder_id = box.create_folder(settings_box["app_backup_dir_id"],("settings", ))
if folder_id==-1:
    print("WARNING: Unable to create settings folder on Box.")
    issues_during_upload = True
else:
    settings_srcdir = Path(rootdir).joinpath("settings")
    if settings_srcdir.exists():
        upload_interrupted = False
        for dirpath, dirnames, filenames in os.walk(settings_srcdir):

            # get relative path of current folder
            dirpath_stem = dirpath.removeprefix(str(settings_srcdir))
            if len(dirpath_stem) == 0:
                current_folder_id = folder_id
            else:
                dirpath_stem_parts = dirpath_stem.strip().removeprefix("/").removeprefix("\\").replace("\\","/").split("/")
                current_folder_id = box.create_folder(folder_id,dirpath_stem_parts)
                if current_folder_id == -1:
                    print("WARNING: Unable to create all settings folders on Box.")
                    upload_interrupted = True
                    break

            # create all subfolders
            for dirname in dirnames:
                subfolder_id = box.create_folder(current_folder_id,(dirname, ))
                if subfolder_id == -1:
                    print("WARNING: Unable to create all settings folders on Box.")
                    upload_interrupted = True
                    break
            if upload_interrupted:
                break

            # upload all files in current folder
            for filename in filenames:
                file_srcpath = Path(dirpath).joinpath(filename)
                res = box.upload_file(str(file_srcpath), current_folder_id)
                if res==-1:
                    print("WARNING: Unable to upload all settings files to Box.")
                    upload_interrupted = True
                    break
            if upload_interrupted:
                break
        
        # check for any errors
        if upload_interrupted:
            issues_during_upload = True

 # backup logs
folder_id = box.create_folder(settings_box["app_backup_dir_id"],("log", ))
if folder_id==-1:
    print("WARNING: Unable to create log folder on Box.")
    issues_during_upload = True
else:
    log_srcdir = Path(rootdir).joinpath("log")
    if log_srcdir.exists():
        upload_interrupted = False
        for dirpath, dirnames, filenames in os.walk(log_srcdir):

            # get relative path of current folder
            dirpath_stem = dirpath.removeprefix(str(log_srcdir))
            if len(dirpath_stem) == 0:
                current_folder_id = folder_id
            else:
                dirpath_stem_parts = dirpath_stem.strip().removeprefix("/").removeprefix("\\").replace("\\","/").split("/")
                current_folder_id = box.create_folder(folder_id,dirpath_stem_parts)
                if current_folder_id == -1:
                    print("WARNING: Unable to create all log folders on Box.")
                    upload_interrupted = True
                    break

            # create all subfolders
            for dirname in dirnames:
                subfolder_id = box.create_folder(current_folder_id,(dirname, ))
                if subfolder_id == -1:
                    print("WARNING: Unable to create all log folders on Box.")
                    upload_interrupted = True
                    break
            if upload_interrupted:
                break

            # upload all files in current folder
            for filename in filenames:
                file_srcpath = Path(dirpath).joinpath(filename)
                res = box.upload_file(str(file_srcpath), current_folder_id)
                if res==-1:
                    print("WARNING: Unable to upload all log files to Box.")
                    upload_interrupted = True
                    break
            if upload_interrupted:
                break
        
        # check for any errors
        if upload_interrupted:
            issues_during_upload = True   


# send notification if there were any issues with the upload
if mail_settings["errors"]["send_notification"] and issues_during_upload:
        notifications.send_email(mail_settings["errors"]["subject"],
                         "Errors encountered when backing up data to Box.", 
                         mail_settings["errors"]["recipients"],
                         mail_settings["mail_server"]["address"],
                         mail_settings["mail_server"]["port"],
                         mail_settings["mail_server"]["user"],
                         mail_settings["mail_server"]["password"])

