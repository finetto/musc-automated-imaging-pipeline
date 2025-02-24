# module with functions allowing to parse names of files on CBI Home

from pathlib import Path
from datetime import datetime
import re

# get session information from filename
def get_timestamp_and_description(filename):

    # get session name by removing file extension
    session_name = Path(filename).stem

    # get date, time and description by splitting the session name
    tmp = session_name.split("_", 2)
    if len(tmp)<3:
        print("WARNING: unexpected naming format for file \"" + filename + "\"")
        return -1
    
    session_date = tmp[0]
    session_time = tmp[1]
    session_description = tmp[2]

    # format date
    if len(session_date) == 8:
        session_date = session_date[:4] + "/" + session_date[4:6] + "/" + session_date[6:8]
    else:
        session_date = None

    # format time
    if len(session_time) == 6:
        session_time = session_time[:2] + ":" + session_time[2:4] + ":" + session_time[4:6]
    else:
        session_time = None

    # generate datetime
    session_datetime = None
    if (session_date != None) and (session_time != None):
        dt_string = " ".join((session_date, session_time))
        session_datetime = datetime.strptime(dt_string, "%Y/%m/%d %H:%M:%S")

    return {"name": session_name, "date": session_date, "time": session_time, "datetime": session_datetime, "description": session_description}

# extract subject ID and session ID from session description
def get_subject_and_session(session_info, subject_format, session_format):

    # get session description
    session_description = "_" + session_info["description"] # prepend "_" as the subject ID could be at the very beginning or later in the string

    # get all potential subject prefix candidates
    desired_prefix = subject_format["desired_prefix"].strip("-_")
    subject_prefix_candidates = ("_" + desired_prefix + "-",
                                 "-" + desired_prefix + "-",
                                 "_" + desired_prefix + "_",
                                 "-" + desired_prefix + "_") # frequent typos with dashes and underscores, so we are looking at all possible combinations
    
    # get all potential session prefix candidates
    desired_prefix = session_format["desired_prefix"].strip("-_")
    session_prefix_candidates = ("_" + desired_prefix + "-",
                                 "-" + desired_prefix + "-",
                                 "_" + desired_prefix + "_",
                                 "-" + desired_prefix + "_") # frequent typos with dashes and underscores, so we are looking at all possible combinations

    # find start of subject and session prefix (if they are available)
    subject_prefix_in_description = False
    subject_prefix_start_index = None
    for subject_prefix in subject_prefix_candidates:
        if subject_prefix in session_description:
            subject_prefix_in_description = True
            subject_prefix_start_index = session_description.find(subject_prefix)

    session_prefix_in_description = False
    session_prefix_start_index = None
    for session_prefix in session_prefix_candidates:
        if session_prefix in session_description:
            session_prefix_in_description = True
            session_prefix_start_index = session_description.find(session_prefix)

    # lets consider the different cases where subject prefix and/or session prefix are present
    subject_id_string = None
    session_id_string = None
    if subject_prefix_in_description and session_prefix_in_description:
        # if subject comes before session, we look for a subject ID between the start of subject prefix and the start of session prefix and for a session ID between the start of session prefix and end of string
        # we do the opposite if session comes before subject
        if session_prefix_start_index>subject_prefix_start_index:
            subject_id_string = session_description[(subject_prefix_start_index+1):session_prefix_start_index]
            session_id_string = session_description[(session_prefix_start_index+1):]
        else:
            session_id_string = session_description[(session_prefix_start_index+1):subject_prefix_start_index]
            subject_id_string = session_description[(subject_prefix_start_index+1):]

    elif subject_prefix_in_description:
        # we look for subject ID in the whole description, while we won't look for a session ID
        subject_id_string = session_description

    elif session_prefix_in_description:
        # we look for a subject ID before the start of the session prefix and for a session ID from the start of the session prefix to the end of the string
        subject_id_string = session_description[:session_prefix_start_index]
        session_id_string = session_description[(session_prefix_start_index+1):]

    else:
        # we look for subject ID in the whole description, while we won't look for a session ID
        subject_id_string = session_description

    # get subject ID
    subject_id = None
    if subject_id_string:

         # check if string follows the requested study ID format
            m = re.search(subject_format["regex"],subject_id_string)
            if m:
                id = m.group().upper() # convert to upper case
                
                # search for the numeric part of the ID
                m2 = re.search("[0-9]+",id)
                if m2:
                    # convert to proper number of digits
                    id_num = int(m2.group())
                    #id = (id[:m2.span()[0]] + "{num:0" + str(subject_format["desired_digits"]) + "d}" + id[m2.span()[1]:]).format(num = id_num)
                    id = (subject_format["desired_start_str"] + "{num:0" + str(subject_format["desired_digits"]) + "d}").format(num = id_num)

                subject_id = subject_format["desired_prefix"] + id

    # get session ID
    session_id = None
    if session_id_string:

        # search for the numeric part of the ID
        m = re.search("[0-9]+",session_id_string)
        if m:
            # convert to proper number of digits
            id_num = int(m.group())
            id = ("{num:0" + str(session_format["desired_digits"]) + "d}").format(num = id_num)
                
            session_id = session_format["desired_prefix"] + id

    return {"subject_id": subject_id, "session_id": session_id}
