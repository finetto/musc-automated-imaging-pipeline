# module with functions allowing to query and download files from CBI Home

import sys
import os
from pathlib import Path
import json
import paramiko
import scp

# get list of available files
def get_sessions(host, data_folder, credentials_file):

    # get SSH credentials from file
    try:
        if Path(credentials_file).exists:
            with open(credentials_file, 'r') as f:
                credentials = json.load(f)
        else:
            print("ERROR: Could not find credentials file.")
            return -1
    except Exception as e:
        print("ERROR: Unable to load credentials file:\n")
        print(e)
        return -1
    
    # connect to server
    try:
        sshClient = paramiko.SSHClient()
        sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sshClient.connect(host,username=credentials["user"],password=credentials["password"],timeout=10)
    except Exception as e:
        print("ERROR: Unable to establish connection to CBI Home:\n")
        print(e)
        return -1
    
    # query data and summary files
    data_files = []
    summary_files = []
    try:
        # get zipped session data
        cmd = "cd " + data_folder + " ; for f in *.zip ; do echo ${f}; done"
        stdin, stdout, stderr = sshClient.exec_command(cmd)

        # check for errors
        errors = ""
        for line in stderr.readlines():
            errors = errors + line
        if errors != "":
            print("ERROR: Something went wrong while executing command on remote host:\n")
            print(errors)
            return -1

        # get output
        for line in stdout.readlines():
            data_files.append(line.strip())

        # get session summary files
        cmd = "cd " + data_folder + " ; for f in *_SUMMARY.txt ; do echo ${f}; done"
        stdin, stdout, stderr = sshClient.exec_command(cmd)

        # check for errors
        errors = ""
        for line in stderr.readlines():
            errors = errors + line
        if errors != "":
            print("ERROR: Something went wrong while executing command on remote host:\n")
            print(errors)
            return -1

        # get output
        for line in stdout.readlines():
            summary_files.append(line.strip())

    except Exception as e:
        print("ERROR: Unable to get available sessions from CBI Home:\n")
        print(e)
        return -1
    
    # close connection and clean up
    sshClient.close()
    del stdin, stdout, stderr
    del sshClient
    
    return {"data_files": data_files, "summary_files": summary_files}

# download a file
def download_file(filename, host, data_folder, credentials_file, destination_folder, show_progress=False):

    # get SSH credentials from file
    try:
        if Path(credentials_file).exists:
            with open(credentials_file, 'r') as f:
                credentials = json.load(f)
        else:
            print("ERROR: Could not find credentials file.")
            return -1
    except Exception as e:
        print("ERROR: Unable to load credentials file:\n")
        print(e)
        return -1
    
    # check if destination folder exists
    if not os.path.exists(destination_folder):
        os.mkdir(destination_folder)
    
    # connect to server
    try:
        sshClient = paramiko.SSHClient()
        sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sshClient.connect(host,username=credentials["user"],password=credentials["password"],timeout=10)

        if show_progress:
            scpClient = scp.SCPClient(sshClient.get_transport(), progress = scp_show_progress)
        else:
            scpClient = scp.SCPClient(sshClient.get_transport())
    except Exception as e:
        print("ERROR: Unable to establish connection to CBI Home:\n")
        print(e)
        return -1
    
    # copy data
    try:
        # download
        scpClient.get(remote_path=os.path.join(data_folder,filename),local_path=os.path.join(destination_folder,filename),preserve_times=True)

        # update progress indicator so the following "print" does not overwrite it
        if show_progress:
            scp_show_progress("", 100, 100, True)

    except Exception as e:
        print("ERROR: Failed to download file from CBI Home:\n")
        print(e)
        return -1

    # close connection and clean up
    scpClient.close()
    sshClient.close()
    del sshClient, scpClient

    return 1

# helper function to show download progress
def scp_show_progress(filename, size, sent, done=False):
    if not done:
        sys.stdout.write("  progress: %.2f%%   \r" % (float(sent)/float(size)*100,) )
    else:
        sys.stdout.write("  progress: %.2f%%   \n" % (100,) )
    sys.stdout.flush()