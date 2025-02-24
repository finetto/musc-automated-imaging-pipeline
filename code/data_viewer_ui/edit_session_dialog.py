# This Python file uses the following encoding: utf-8
import sys
import os
import re
from datetime import datetime

from PySide6.QtWidgets import QWidget, QDialog, QMessageBox, QSpinBox, QInputDialog, QLineEdit

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
rootdir = os.path.dirname(parentdir)

sys.path.insert(0, parentdir) 
from common import database, database_settings
from common import study, study_settings

import data_viewer_utils

from ui_edit_session_dialog import Ui_edit_session_dialog

class edit_session_dialog(QDialog):

    _settings_db = None
    _settings_study = None
    _mode = None
    _session_row_id = None

    _all_study_ids = ()
    _all_deidentified_ids = ()
    _all_group_assignments = ()

    _session_id_spinbox = None

    session_went_from_skipped_to_notskipped = False

    def __init__(self, parent=None, session_row_id=None, mode="edit", settings_database=None, settings_study=None, session_description=""):

        super().__init__(parent)
        self.ui = Ui_edit_session_dialog()
        self.ui.setupUi(self)

        # get study settings
        self._settings_study = settings_study

        if settings_study != None:
            session_id_prefix = settings_study["session_identifier_format"]["desired_prefix"]
            session_id_digits = settings_study["session_identifier_format"]["desired_digits"]
        else:
            session_id_prefix = "ses-"
            session_id_digits = 2

        # set session description
        if session_description == "":
            self.ui.label_session_description.setText("")
        else:
            self.ui.label_session_description.setText(session_description)

        # initialize custom spinbox for session ID
        self._session_id_spinbox = CustomSpinBox(session_id_digits,self)
        self.ui.session_id_placeholder.addWidget(self._session_id_spinbox)
        self._session_id_spinbox.setPrefix(session_id_prefix)
        self._session_id_spinbox.setMinimum(0)
        self._session_id_spinbox.setMaximum(10**session_id_digits-1)

        # define connections to signals
        self.ui.pushButton_ok.clicked.connect(self.pushButton_ok_clicked)
        self.ui.pushButton_cancel.clicked.connect(self.pushButton_cancel_clicked)

        self.ui.comboBox_subject_id.currentIndexChanged.connect(self.comboBox_subject_id_selection_changed)
        self.ui.pushButton_new_subject_id.clicked.connect(self.pushButton_new_subject_id_clicked)

        self.ui.lineEdit_deidentified_id.editingFinished.connect(self.lineEdit_deidentified_id_edited)
        self.ui.pushButton_generate_deidentifdied_id.clicked.connect(self.pushButton_generate_deidentifdied_id_clicked)

        self.ui.comboBox_group_assignment.currentIndexChanged.connect(self.comboBox_group_assignment_selection_changed)

        self._session_id_spinbox.valueChanged.connect(self.spinBox_session_id_value_changed)

        self.ui.checkBox_skip_processing.stateChanged.connect(self.checkBox_skip_processing_state_changed)

        self._mode = None
        self._settings_db = None


        # copy session data
        self._session_row_id = session_row_id
        if session_row_id == None:
            # something is wrong
            res = QMessageBox.critical(self, "Data Viewer", "Invalid session ID.")

        # parse mode
        match mode:
            case "validate":
                self.setWindowTitle("Validate Session Data")
                self._mode = mode
            case "edit":
                self.setWindowTitle("Edit Session Data")
                self._mode = mode
            case _:
                # something is wrong
                res = QMessageBox.critical(self, "Data Viewer", "Invalid mode selected.")

        # copy settings
        self._settings_db = settings_database
        if settings_database == None:
            # something is wrong
            res = QMessageBox.critical(self, "Data Viewer", "Invalid database settings.")

        # initialize UI
        if (self._session_row_id != None) and (self._settings_db != None) and (self._mode != None):
            self.initialize_ui()
        else:
            # disable GUI elements
            self.ui.groupBox_participant.setEnabled(False)
            self.ui.groupBox_session.setEnabled(False)

    def initialize_ui(self):
        
        if (self._settings_db == None) or (self._settings_db == -1):
            return

        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        # get all paricipants
        participants = db.get_all_participant_data()
        if participants == -1:
            res = QMessageBox.critical(self, "Data Viewer", "Could not get all participant data.")
            participants = None

        # get all study IDs and deidentified IDs
        all_study_ids, all_deidentified_ids = data_viewer_utils.get_all_ids(participants)
        self._all_study_ids = all_study_ids
        self._all_deidentified_ids = all_deidentified_ids

        # define all possible group assignments
        all_group_assignments = ("patient", "control", "test")
        self._all_group_assignments = all_group_assignments

        # get data of selected session
        session_data = None
        if self._session_row_id != None:
            session_data = db.get_mri_session_data(id=self._session_row_id, return_only_first=True)
            if session_data == -1:
                res = QMessageBox.critical(self, "Data Viewer", "Could not get MRI session data.")
                session_data = None
            
        if session_data != None:
            participant_id = session_data["participant_id"]
            session_id = session_data["participant_session_id"]
            skip_processing = session_data["skip_processing"] == 1
        else:
            participant_id = None
            session_id = None
            skip_processing = False

        # get data of corresponding participant
        study_id, deidentified_id, group_assignment = data_viewer_utils.get_participant_data_for_session(self, db, participant_id)

        # check if any participant is selected
        any_participant_selected = study_id != None

        # check if participant can be edited (has no converted sessions)
        participant_is_editable = data_viewer_utils.get_participant_editable(self, db, participant_id)

        # populate UI
        all_items = list(all_study_ids)
        all_items.insert(0,"Select ID")
        self.ui.comboBox_subject_id.blockSignals(True)
        self.ui.comboBox_subject_id.clear()
        self.ui.comboBox_subject_id.addItems(all_items)
        if any_participant_selected:
            self.ui.comboBox_subject_id.setCurrentText(study_id)
        self.ui.comboBox_subject_id.blockSignals(False)

        self.ui.lineEdit_deidentified_id.blockSignals(True)
        if deidentified_id != None:
            self.ui.lineEdit_deidentified_id.setText(deidentified_id)
        else:
            self.ui.lineEdit_deidentified_id.setText("")      
        self.ui.lineEdit_deidentified_id.setEnabled(any_participant_selected and participant_is_editable)
        self.ui.lineEdit_deidentified_id.blockSignals(False)
        self.ui.pushButton_generate_deidentifdied_id.setEnabled(any_participant_selected and participant_is_editable)

        all_items = list(all_group_assignments)
        all_items.insert(0,"Select Group")
        self.ui.comboBox_group_assignment.blockSignals(True)
        self.ui.comboBox_group_assignment.clear()
        self.ui.comboBox_group_assignment.addItems(all_items)
        if group_assignment != None:
            self.ui.comboBox_group_assignment.setCurrentText(group_assignment)
        self.ui.comboBox_group_assignment.setEnabled(any_participant_selected and participant_is_editable)
        self.ui.comboBox_group_assignment.blockSignals(False)

        if session_id != None:
            m = re.search("\d+",session_id)
            if m:
                session_number = int(m.group())
            else:
                session_number = 0
        else:
            session_number = 0
        self._session_id_spinbox.blockSignals(True)
        self._session_id_spinbox.setValue(session_number)
        self._session_id_spinbox.blockSignals(False)

        self.ui.checkBox_skip_processing.blockSignals(True)
        self.ui.checkBox_skip_processing.setChecked(skip_processing)
        self.ui.checkBox_skip_processing.blockSignals(False)

        # close connection to database
        db.close()



    # save and exit
    def pushButton_ok_clicked(self):

        if (self._session_row_id != None) and (self._settings_db != None) and (self._settings_db != -1):
            
            # connect to database
            db = database.db(self._settings_db["db_path"])
            db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

            # get current data for session
            current_session_data = db.get_mri_session_data(id=self._session_row_id, return_only_first=True)
            if current_session_data == -1:
                current_session_data = None
            
            if current_session_data != None:
                current_participant_id = current_session_data["participant_id"]
                current_session_id = current_session_data["participant_session_id"]
                current_skip_processing = current_session_data["skip_processing"] == 1
            else:
                current_participant_id = None
                current_session_id = None
                current_skip_processing = False

            # get study id and participant id of selected participant
            if self.ui.comboBox_subject_id.currentIndex() != 0:
                new_study_id = self.ui.comboBox_subject_id.currentText()
            else:
                new_study_id = None

            if new_study_id != None:
                new_participant_id = db.get_participant_id(study_id=new_study_id)
                if new_participant_id == -1:
                    new_participant_id = None
            else:
                new_participant_id = None

            # get current data for selected participant, and check if participant can be edited
            if new_participant_id != None:
                _, current_deidentified_id, current_group_assignment = data_viewer_utils.get_participant_data_for_session(self, db, new_participant_id)
                participant_is_editable = data_viewer_utils.get_participant_editable(self, db, new_participant_id)
            else:
                current_deidentified_id = None
                current_group_assignment = None
                participant_is_editable = False

            # get new deidentified id
            new_deidentified_id = self.ui.lineEdit_deidentified_id.text()

            # get new group assignment
            if self.ui.comboBox_group_assignment.currentIndex() != 0:
                new_group_assignment = self.ui.comboBox_group_assignment.currentText()
            else:
                new_group_assignment = None

            # get new session id
            session_id_num = self._session_id_spinbox.value()
            if session_id_num > 0:
                session_id_prefix = self._settings_study["session_identifier_format"]["desired_prefix"]
                session_id_digits = self._settings_study["session_identifier_format"]["desired_digits"]
                new_session_id = data_viewer_utils.get_session_id_from_number(session_id_num, session_id_prefix, session_id_digits)
            else:
                new_session_id = None

            # get new skip processing flag
            new_skip_processing = self.ui.checkBox_skip_processing.isChecked()


            # update participant
            if (new_participant_id != None) and participant_is_editable:

                if (new_deidentified_id != None) and (new_deidentified_id != current_deidentified_id):
                    db.update_participant(id=new_participant_id, deidentified_id=new_deidentified_id)

                if (new_group_assignment != None) and (new_group_assignment != current_group_assignment):
                    db.update_participant(id=new_participant_id, group_assignment=new_group_assignment)

            # update session
            if (new_participant_id != None) and (new_participant_id != current_participant_id):
                db.update_mri_session(id=self._session_row_id, participant_id=new_participant_id)

            if (new_session_id != None) and (new_session_id != current_session_id):
                db.update_mri_session(id=self._session_row_id, participant_session_id=new_session_id)

            if (new_skip_processing != None) and (new_skip_processing != current_skip_processing):
                db.update_mri_session(id=self._session_row_id, skip_processing=new_skip_processing)
                
                if new_skip_processing == False:
                    self.session_went_from_skipped_to_notskipped = True

            validation_dt = datetime.now().timestamp()
            db.update_mri_session(id=self._session_row_id, study_id_validated_dt=validation_dt, session_id_validated_dt=validation_dt)

            # commit changes
            db.commit()

            # close connection to database
            db.close()

        self.accept()

    # exit without saving
    def pushButton_cancel_clicked(self):
        self.close()

    def comboBox_subject_id_selection_changed(self, index):

        # check if any participant was selected
        if index == 0:

            # clear and disable deidentified id elements
            self.ui.lineEdit_deidentified_id.blockSignals(True)
            self.ui.lineEdit_deidentified_id.setText("")
            self.ui.lineEdit_deidentified_id.setEnabled(False)
            self.ui.pushButton_generate_deidentifdied_id.setEnabled(False)
            self.ui.lineEdit_deidentified_id.blockSignals(False)

            # clear and disable group assignment
            self.ui.comboBox_group_assignment.blockSignals(True)
            self.ui.comboBox_group_assignment.setCurrentIndex(0)
            self.ui.comboBox_group_assignment.setEnabled(False)
            self.ui.comboBox_group_assignment.blockSignals(False)

            return
        
        # get study id
        study_id = self.ui.comboBox_subject_id.currentText()

        # check db settings
        if (self._settings_db == None) or (self._settings_db == -1):
            return

        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        # get participant id and data
        participant_id = db.get_participant_id(study_id=study_id)

        # get data of corresponding participant
        _, deidentified_id, group_assignment = data_viewer_utils.get_participant_data_for_session(self, db, participant_id)

        # check if participant can be edited (has no converted sessions)
        participant_is_editable = data_viewer_utils.get_participant_editable(self, db, participant_id)

        # update other UI elements
        self.ui.lineEdit_deidentified_id.blockSignals(True)
        if deidentified_id != None:
            self.ui.lineEdit_deidentified_id.setText(deidentified_id)
        else:
            self.ui.lineEdit_deidentified_id.setText("")      
        self.ui.lineEdit_deidentified_id.setEnabled(participant_is_editable)
        self.ui.lineEdit_deidentified_id.blockSignals(False)
        self.ui.pushButton_generate_deidentifdied_id.setEnabled(participant_is_editable)

        self.ui.comboBox_group_assignment.blockSignals(True)
        self.ui.comboBox_group_assignment.setCurrentText(group_assignment)
        self.ui.comboBox_group_assignment.setEnabled(participant_is_editable)
        self.ui.comboBox_group_assignment.blockSignals(False)

        # close connection to database
        db.close()

        # trigger session id spinbox callback, since it also validates the session id for this participant
        self.spinBox_session_id_value_changed()

    def pushButton_new_subject_id_clicked(self):
        
        # get desired format
        desired_prefix = self._settings_study["subject_identifier_format"]["desired_prefix"]
        desired_start_str = self._settings_study["subject_identifier_format"]["desired_start_str"]
        desired_digits = self._settings_study["subject_identifier_format"]["desired_digits"]
        id_format = desired_prefix + desired_start_str + "{:0" + str(desired_digits) + "d}"

        # ask user for new id
        new_subject_id, ok = QInputDialog.getText(self, "Data Viewer", "Enter new subject ID:", QLineEdit.Normal, id_format.format(0))
        if not ok:
            return
        if (new_subject_id == "") or (new_subject_id==id_format.format(0)):
            res = QMessageBox.warning(self,"Data Viewer","Invalid subject ID.")
            return
        
        # make sure ID is unique
        if new_subject_id in self._all_study_ids:
            res = QMessageBox.warning(self, "Data Viewer", "This study ID is already used by a different participant.")
            return

        # validate id
        new_id_is_valid, alternative_new_id = data_viewer_utils.validate_id(new_subject_id, desired_prefix, desired_start_str, desired_digits)

        if not new_id_is_valid:

            # make sure alternative ID is unique
            if alternative_new_id in self._all_study_ids:
                    res = QMessageBox.warning(self,"Data Viewer","Could not generate a unique ID from the input.")
                    return

            # ask user what to do
            if alternative_new_id != "":

                res = QMessageBox.warning(self, "Data Viewer", 
                                          "This study ID is not valid. Do you accept this alternative?\n\n" + alternative_new_id,
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

                if res == QMessageBox.Yes:
                    new_subject_id = alternative_new_id
                    
                else:
                    return

            else:
                res = QMessageBox.warning(self,"Data Viewer","Invalid subject ID.")
                return
            
        # ask user to confirm
        res = QMessageBox.question(self,"Data Viewer","Participant " + new_subject_id + " will be added to the database.\nPlease confirm")
        if res != QMessageBox.Yes:
            return
        
        # generate new deidentified id
        new_deidentified_id = study.generate_deidentified_id(used_ids=self._all_deidentified_ids, 
                                                                 prefix=self._settings_study["deidentified_subject_identifier_format"]["desired_prefix"]+self._settings_study["deidentified_subject_identifier_format"]["desired_start_str"],
                                                                 digits=self._settings_study["deidentified_subject_identifier_format"]["desired_digits"])

        # add participant to database

        # check db settings
        if (self._settings_db == None) or (self._settings_db == -1):
            return

        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        participant_id = db.add_participant(study_id=new_subject_id, 
                                                deidentified_id=new_deidentified_id,
                                                group_assignment="patient")
        if participant_id == -1:
            res = QMessageBox.critical(self,"Data Viewer","Could not add new participant to database.")

        db.commit()

        # close connection to database
        db.close()

        # reload database
        self.initialize_ui()

        # select the new participant
        # note: this will also trigger the combobox callback, so de-identified ID and group assignment will also be updated in the UI
        if participant_id != -1:
            self.ui.comboBox_subject_id.setCurrentText(new_subject_id)

    def lineEdit_deidentified_id_edited(self):
        
        # get deidentified id and study id
        new_deidentified_id = self.ui.lineEdit_deidentified_id.text()

        if self.ui.comboBox_subject_id.currentIndex() != 0:
            study_id = self.ui.comboBox_subject_id.currentText()
        else:
            return
        
        # check db settings
        if (self._settings_db == None) or (self._settings_db == -1):
            return

        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        # get participant id and data
        participant_id = db.get_participant_id(study_id=study_id)

        # get data of corresponding participant
        _, current_deidentified_id, group_assignment = data_viewer_utils.get_participant_data_for_session(self, db, participant_id)

        # check if participant can be edited (has no converted sessions)
        participant_is_editable = data_viewer_utils.get_participant_editable(self, db, participant_id)

        # close connection to database
        db.close()

        # make sure participant is editable (should always be the case)
        if not participant_is_editable:
            # reset id
            self.ui.lineEdit_deidentified_id.blockSignals(True)
            self.ui.lineEdit_deidentified_id.setText(current_deidentified_id)
            self.ui.lineEdit_deidentified_id.blockSignals(False)

            return
        
        # make sure the new id is different from the previous one
        if new_deidentified_id == current_deidentified_id:
            return
        
        # check if deidentified id is empty
        if new_deidentified_id == "":
            res = QMessageBox.warning(self, "Data Viewer", 
                                          "Are you sure you would like to clear the de-identified ID? Data won't be de-identified.",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

            if res == QMessageBox.Yes:
                return

        # make sure ID is unique
        if new_deidentified_id in self._all_deidentified_ids:
            res = QMessageBox.warning(self, "Data Viewer", "This deidentified ID is already used by a different participant.")
            
            # reset id
            self.ui.lineEdit_deidentified_id.blockSignals(True)
            self.ui.lineEdit_deidentified_id.setText(current_deidentified_id)
            self.ui.lineEdit_deidentified_id.blockSignals(False)

            return
        
        # make sure ID conforms to specified standard. Otherwise, alert user
        desired_prefix = self._settings_study["deidentified_subject_identifier_format"]["desired_prefix"]
        desired_start_str = self._settings_study["deidentified_subject_identifier_format"]["desired_start_str"]
        desired_digits = self._settings_study["deidentified_subject_identifier_format"]["desired_digits"]
        
        new_id_is_valid, alternative_new_id = data_viewer_utils.validate_id(new_deidentified_id, desired_prefix, desired_start_str, desired_digits)

        if not new_id_is_valid:

            # make sure alternative ID is valid
            if (alternative_new_id != "") and (alternative_new_id != current_deidentified_id) and (alternative_new_id in self._all_deidentified_ids):
                    alternative_new_id = ""

            # ask user what to do
            if alternative_new_id != "":

                res = QMessageBox.warning(self, "Data Viewer", 
                                          "This deidentified ID is not valid. Do you accept this alternative?\n\n" + alternative_new_id,
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

                if res == QMessageBox.Yes:
                    # set new id
                    self.ui.lineEdit_deidentified_id.blockSignals(True)
                    self.ui.lineEdit_deidentified_id.setText(alternative_new_id)
                    self.ui.lineEdit_deidentified_id.blockSignals(False)
                    
                else:
                    # reset id
                    self.ui.lineEdit_deidentified_id.blockSignals(True)
                    self.ui.lineEdit_deidentified_id.setText(current_deidentified_id)
                    self.ui.lineEdit_deidentified_id.blockSignals(False)

            else:
                res = QMessageBox.warning(self, "Data Viewer", "This deidentified ID is not valid. The field will be reset to the original value.")

                # reset id
                self.ui.lineEdit_deidentified_id.blockSignals(True)
                self.ui.lineEdit_deidentified_id.setText(current_deidentified_id)
                self.ui.lineEdit_deidentified_id.blockSignals(False)


        

    def pushButton_generate_deidentifdied_id_clicked(self):
        
        # generate new deidentified id
        new_deidentified_id = study.generate_deidentified_id(used_ids=self._all_deidentified_ids, 
                                                                 prefix=self._settings_study["deidentified_subject_identifier_format"]["desired_prefix"]+self._settings_study["deidentified_subject_identifier_format"]["desired_start_str"],
                                                                 digits=self._settings_study["deidentified_subject_identifier_format"]["desired_digits"])
        
        # set new id
        self.ui.lineEdit_deidentified_id.blockSignals(True)
        self.ui.lineEdit_deidentified_id.setText(new_deidentified_id)
        self.ui.lineEdit_deidentified_id.blockSignals(False)


    def comboBox_group_assignment_selection_changed(self, index):
        # do nothing
        pass

    def spinBox_session_id_value_changed(self, value=None):

        # get value if not provided
        if value==None:
            value = self._session_id_spinbox.value()

        # make sure value is valid
        if value <= 0:
            res = QMessageBox.warning(self, "Data Viewer", "Invalid session id.")
            return
        
        # make sure a participant was selected and get participant study id
        if self.ui.comboBox_subject_id.currentIndex() != 0:
            study_id = self.ui.comboBox_subject_id.currentText()
        else:
            return
        
        # get new session id
        session_id_prefix = self._settings_study["session_identifier_format"]["desired_prefix"]
        session_id_digits = self._settings_study["session_identifier_format"]["desired_digits"]
        new_session_id = data_viewer_utils.get_session_id_from_number(value, session_id_prefix, session_id_digits)

        # make sure session id is unique. If not, ask user what to do
        # check db settings
        if (self._settings_db == None) or (self._settings_db == -1):
            return

        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        # get participant id
        participant_id = db.get_participant_id(study_id=study_id)
        if participant_id == -1:
            participant_id = None

        # get data of selected session
        current_session_data = None
        if self._session_row_id != None:
            current_session_data = db.get_mri_session_data(id=self._session_row_id, return_only_first=True)
            if current_session_data == -1:
                current_session_data = None
        
        current_session_id = None
        current_study_id = None
        if current_session_data != None:
            current_participant_id = current_session_data["participant_id"]
            current_session_id = current_session_data["participant_session_id"]

            # get data of corresponding participant
            current_study_id, _, _ = data_viewer_utils.get_participant_data_for_session(self, db, current_participant_id)

        # get all sessions for selected participant
        if participant_id != None:
            all_participant_sessions = db.get_mri_session_data(participant_id=participant_id)
            if all_participant_sessions == -1:
                all_participant_sessions = None

        # get all session IDs
        all_participant_session_ids = []
        if all_participant_sessions != None:
            for session in all_participant_sessions:
                id = session["participant_session_id"]
                if (id != None) and (id != ""):
                    all_participant_session_ids.append(id)

        # close connection to database
        db.close()

        if ((study_id != current_study_id) or (new_session_id != current_session_id)) and (new_session_id in all_participant_session_ids):
            res = QMessageBox.question(self, "Data Viewer", "Session ID '" + new_session_id + "' is already assigned to a different session. Would you still like to use it?")
            if res != QMessageBox.Yes:

                # reset to previous id
                if current_session_id != None:
                    m = re.search("\d+",current_session_id)
                    if m:
                        session_number = int(m.group())
                    else:
                        session_number = 0
                else:
                    session_number = 0
                self._session_id_spinbox.blockSignals(True)
                self._session_id_spinbox.setValue(session_number)
                self._session_id_spinbox.blockSignals(False)



    def checkBox_skip_processing_state_changed(self, state):
        
        # if checked, ask user if they are sure
        if state:
            res = QMessageBox.question(self, "Data Viewer", 
                                          "All future automated processing will be disabled for this session. Unprocessed data will be removed. Are you sure?")
            if res != QMessageBox.Yes:
                self.ui.checkBox_skip_processing.blockSignals(True)
                self.ui.checkBox_skip_processing.setChecked(False)
                self.ui.checkBox_skip_processing.blockSignals(False)


class CustomSpinBox(QSpinBox):

    _digits = None
    _format = ""

    def __init__(self, digits, *args):
       self._digits = digits
       self._format = "{:0" + str(self._digits) + "d}"
       QSpinBox.__init__(self, *args)

    def textFromValue(self, value):
       return self._format.format(value)
