import sys
import os
import re

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
rootdir = os.path.dirname(parentdir)

sys.path.insert(0, parentdir) 
from common import database, database_settings
from common import study, study_settings

from PySide6.QtWidgets import QMessageBox

# get participand data for session
def get_participant_data_for_session(parent, db, participant_id):
    participant = None
    if participant_id != None:
        participant = db.get_participant_data(id=participant_id, return_only_first=True)
        if participant == -1:
            res = QMessageBox.critical(parent, "Data Viewer", "Unable to get participant data.")
            participant = None
        
    if participant != None:
        study_id = participant["study_id"]
        deidentified_id = participant["deidentified_id"]
        group_assignment = participant["group_assignment"]
    else:
        study_id = None
        deidentified_id = None
        group_assignment = None

    return study_id, deidentified_id, group_assignment

# get all study IDs and deidentified IDs
def get_all_ids(participants):
    all_study_ids = []
    all_deidentified_ids = []

    if participants == None:
        return tuple(all_study_ids), tuple(all_deidentified_ids)

    for participant in participants:
        if (participant["study_id"]!=None) and (participant["study_id"]!=""):
            all_study_ids.append(participant["study_id"])
        if (participant["deidentified_id"]!=None) and (participant["deidentified_id"]!=""):
            all_deidentified_ids.append(participant["deidentified_id"])

    return tuple(all_study_ids), tuple(all_deidentified_ids)

# check if participant is editable (has no converted sessions)
def get_participant_editable(parent, db, participant_id):
    if participant_id != None:
        participant_sessions = db.get_mri_session_data(participant_id=participant_id)
        if participant_sessions==-1:
            res = QMessageBox.critical(parent, "Data Viewer", "Could not get participant sessions.")
            participant_sessions = None

        participant_is_editable = True
        if participant_sessions != None:
            for participant_session in participant_sessions:
                data_converted_dt = participant_session["data_converted_dt"]
                if data_converted_dt != None:
                    participant_is_editable = False
                    break

    else:
        participant_sessions = None
        participant_is_editable = True

    return participant_is_editable

# validate ID and provide potential alternative
def validate_id(id, desired_prefix, desired_start_str, desired_digits):
    
    # format used to generate new ID
    id_format = desired_prefix + desired_start_str + "{:0" + str(desired_digits) + "d}"

    id_is_valid = True
    alternative_id = id

    # search for correct pattern
    m = re.search(desired_prefix + desired_start_str + "\d+",id)
    if m: # pattern found
        extracted_id = m.group()
        id_start = m.span()[0]
        id_end = m.span()[1]
        alternative_id = extracted_id

        # make sure there are no extra characters at the beginning or end of original ID string
        if (id_start != 0) or (id_end != len(id)):
            id_is_valid = False

        # verify correct number of digits
        m2 = re.search("\d+",extracted_id)
        if m2:
            numeric_part = m2.group()
            if len(numeric_part) < desired_digits:
                id_is_valid = False
                alternative_id = id_format.format(int(numeric_part))
            elif len(numeric_part) > desired_digits:
                # trim string
                id_is_valid = False
                alternative_id = desired_prefix + desired_start_str + numeric_part[:desired_digits]

        else: # this should never be the case
            id_is_valid = False
            alternative_id = ""
        

    else: # pattern not found
        id_is_valid = False

        # check if id contains any digits
        m2 = re.search("\d+",id)
        if m2:
            numeric_part = m2.group()
            if len(numeric_part) <= desired_digits:
                alternative_id = id_format.format(int(numeric_part))
            elif len(numeric_part) > desired_digits:
                # trim string
                alternative_id = desired_prefix + desired_start_str + numeric_part[:desired_digits]

        else:
            alternative_id = ""

    return id_is_valid, alternative_id

def get_session_id_from_number(id_number, prefix, digits):
    id_format = prefix + "{:0" + str(digits) + "d}"
    return id_format.format(id_number)