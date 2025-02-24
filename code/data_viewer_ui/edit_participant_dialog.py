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

from ui_edit_participant_dialog import Ui_edit_participant_dialog

class edit_participant_dialog(QDialog):

    _settings_db = None
    _settings_study = None
    _participant_row_id = None

    _all_deidentified_ids = ()
    _all_group_assignments = ()

    def __init__(self, parent=None, participant_row_id=None, settings_database=None, settings_study = None, subject_id=""):

        super().__init__(parent)
        self.ui = Ui_edit_participant_dialog()
        self.ui.setupUi(self)

        self.setWindowTitle("Edit Participant")

        # get study settings
        self._settings_study = settings_study

        # set subject ID
        if subject_id == "":
            self.ui.label_subject_id.setText("")
        else:
            self.ui.label_subject_id.setText(subject_id)

        # define connections to signals
        self.ui.pushButton_ok.clicked.connect(self.pushButton_ok_clicked)
        self.ui.pushButton_cancel.clicked.connect(self.pushButton_cancel_clicked)

        self.ui.lineEdit_deidentified_id.editingFinished.connect(self.lineEdit_deidentified_id_edited)
        self.ui.pushButton_generate_deidentifdied_id.clicked.connect(self.pushButton_generate_deidentifdied_id_clicked)

        self.ui.comboBox_group_assignment.currentIndexChanged.connect(self.comboBox_group_assignment_selection_changed)

        self._settings_db = None


        # copy session data
        self._participant_row_id = participant_row_id
        if participant_row_id == None:
            # something is wrong
            res = QMessageBox.critical(self, "Data Viewer", "Invalid subject ID.")

        # copy settings
        self._settings_db = settings_database
        if settings_database == None:
            # something is wrong
            res = QMessageBox.critical(self, "Data Viewer", "Invalid database settings.")

        # initialize UI
        if (self._participant_row_id != None) and (self._settings_db != None):
            self.initialize_ui()
        else:
            # disable GUI elements
            self.ui.groupBox_participant.setEnabled(False)

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

        # get data of selected participant, and check if participant can be edited
        if self._participant_row_id != None:
            _, deidentified_id, group_assignment = data_viewer_utils.get_participant_data_for_session(self, db, self._participant_row_id)
            participant_is_editable = data_viewer_utils.get_participant_editable(self, db, self._participant_row_id)
        else:
            deidentified_id = None
            group_assignment = None
            participant_is_editable = False

        # populate UI
        self.ui.lineEdit_deidentified_id.blockSignals(True)
        if deidentified_id != None:
            self.ui.lineEdit_deidentified_id.setText(deidentified_id)
        else:
            self.ui.lineEdit_deidentified_id.setText("")      
        self.ui.lineEdit_deidentified_id.setEnabled(participant_is_editable)
        self.ui.lineEdit_deidentified_id.blockSignals(False)
        self.ui.pushButton_generate_deidentifdied_id.setEnabled(participant_is_editable)

        all_items = list(all_group_assignments)
        all_items.insert(0,"Select Group")
        self.ui.comboBox_group_assignment.blockSignals(True)
        self.ui.comboBox_group_assignment.clear()
        self.ui.comboBox_group_assignment.addItems(all_items)
        if group_assignment != None:
            self.ui.comboBox_group_assignment.setCurrentText(group_assignment)
        self.ui.comboBox_group_assignment.setEnabled(participant_is_editable)
        self.ui.comboBox_group_assignment.blockSignals(False)

        # close connection to database
        db.close()



    # save and exit
    def pushButton_ok_clicked(self):

        if (self._participant_row_id != None) and (self._settings_db != None) and (self._settings_db != -1):
            
            # connect to database
            db = database.db(self._settings_db["db_path"])
            db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

            # get current data for selected participant, and check if participant can be edited
            _, current_deidentified_id, current_group_assignment = data_viewer_utils.get_participant_data_for_session(self, db, self._participant_row_id)
            participant_is_editable = data_viewer_utils.get_participant_editable(self, db, self._participant_row_id)

            # get new deidentified id
            new_deidentified_id = self.ui.lineEdit_deidentified_id.text()

            # get new group assignment
            if self.ui.comboBox_group_assignment.currentIndex() != 0:
                new_group_assignment = self.ui.comboBox_group_assignment.currentText()
            else:
                new_group_assignment = None

            # update participant
            if participant_is_editable:

                if (new_deidentified_id != None) and (new_deidentified_id != current_deidentified_id):
                    db.update_participant(id=self._participant_row_id, deidentified_id=new_deidentified_id)

                if (new_group_assignment != None) and (new_group_assignment != current_group_assignment):
                    db.update_participant(id=self._participant_row_id, group_assignment=new_group_assignment)

                # commit changes
                db.commit()

            # close connection to database
            db.close()

        self.accept()

    # exit without saving
    def pushButton_cancel_clicked(self):
        self.close()

    def lineEdit_deidentified_id_edited(self):
        
        # get deidentified id and study id
        new_deidentified_id = self.ui.lineEdit_deidentified_id.text()
        
        # check db settings
        if (self._settings_db == None) or (self._settings_db == -1):
            return

        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        # get data of selected participant
        _, current_deidentified_id, group_assignment = data_viewer_utils.get_participant_data_for_session(self, db, self._participant_row_id)

        # check if participant can be edited (has no converted sessions)
        participant_is_editable = data_viewer_utils.get_participant_editable(self, db, self._participant_row_id)

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
