# This Python file uses the following encoding: utf-8
from pathlib import Path
import shutil
import sys
import os
from functools import partial
from datetime import datetime
import json

from PySide6.QtWidgets import QApplication, QWidget, QTableWidgetItem, QPushButton, QMessageBox, QInputDialog, QLineEdit, QListWidgetItem
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
rootdir = os.path.dirname(parentdir)

sys.path.insert(0, parentdir) 
from common import database, database_settings
from common import study, study_settings
from common import processing_settings

import data_viewer_utils

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_data_viewer_ui import Ui_data_viewer_ui
from edit_participant_dialog import edit_participant_dialog
from edit_session_dialog import edit_session_dialog
from reprocess_session_dialog import reprocess_session_dialog

class data_viewer_ui(QWidget):

    _settings_db = None
    _settings_study = None
    _settings_processing = None

    _all_study_ids = ()
    _all_deidentified_ids = ()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_data_viewer_ui()
        self.ui.setupUi(self)

        # define connections to signals
        self.ui.pushButton_new_participant.clicked.connect(self.pushButton_new_participant_clicked)
        self.ui.pushButton_reload_db.clicked.connect(self.load_db)
        self.ui.listWidget_mri_session_series.currentItemChanged.connect(self.update_session_series_table)

        # get database settings from file
        db_settings_file = os.path.join(rootdir,"settings","database_settings.json")
        self._settings_db = database_settings.load_from_file(db_settings_file)
        if self._settings_db == -1:
            res = QMessageBox.critical(self, "Data Viewer", "Unable to load database settings from \"" + db_settings_file + "\".")
            self._settings_db = None

        # get study settings from file
        study_settings_file = os.path.join(rootdir,"settings","study_settings.json")
        self._settings_study = study_settings.load_from_file(study_settings_file)
        if self._settings_study == -1:
            res = QMessageBox.critical(self, "Data Viewer", "Could not load study settings.")
            self._settings_study = None

        # get processing settings from file
        processing_settings_file = os.path.join(rootdir,"settings","processing_settings.json")
        self._settings_processing = processing_settings.load_from_file(processing_settings_file)
        if self._settings_processing == -1:
            res = QMessageBox.critical(self, "Data Viewer", "Could not load processing settings.")
            self._settings_processing = None

        # load data from db and populate tables
        self.load_db()

    def closeEvent(self, event):

        # quit
        app.quit()

    def load_db(self):

        if (self._settings_db == None) or (self._settings_db == -1):
            return

        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        # get paricipants
        participants = db.get_all_participant_data(sort_column="id", sort_dir="descending")
        if participants == -1:
            res = QMessageBox.critical(self, "Data Viewer", "Unable to get all participant data.")

        # get all study IDs and deidentified IDs
        all_study_ids, all_deidentified_ids = data_viewer_utils.get_all_ids(participants)
        self._all_study_ids = all_study_ids
        self._all_deidentified_ids = all_deidentified_ids

        # get mri sessions
        mri_sessions = db.get_all_mri_session_data(sort_column="data_recorded_dt", sort_dir="descending")
        if mri_sessions == -1:
            res = QMessageBox.critical(self, "Data Viewer", "Unable to get all MRI session data data.")

        # get mri series
        mri_series = db.get_all_mri_series_data()
        if mri_series == -1:
            res = QMessageBox.critical(self, "Data Viewer", "Unable to get all MRI series data.")

        # populate participant table
        self.ui.tableWidget_participants.clear()
        self.ui.tableWidget_participants.setColumnCount(4)
        self.ui.tableWidget_participants.setHorizontalHeaderLabels(("Subject ID", "De-identified ID", "Group", ""))

        if isinstance(participants,list):
            self.ui.tableWidget_participants.setRowCount(len(participants))
            row_ind = -1
            for participant in participants:

                # parse participant data
                record_id = participant["id"]
                study_id = participant["study_id"]
                deidentified_id = participant["deidentified_id"]
                group_assignment = participant["group_assignment"]
                row_ind = row_ind+1

                # check if participant can be edited (has no converted sessions)
                participant_is_editable = data_viewer_utils.get_participant_editable(self, db, record_id)

                # populate table
                self.ui.tableWidget_participants.setItem(row_ind,0,QTableWidgetItem(study_id))
                self.ui.tableWidget_participants.setItem(row_ind,1,QTableWidgetItem(deidentified_id))
                self.ui.tableWidget_participants.setItem(row_ind,2,QTableWidgetItem(group_assignment))

                if participant_is_editable:
                    bt = QPushButton("Edit")
                    bt.clicked.connect(partial(self.edit_participant_button_pressed,self.ui.tableWidget_participants, row_ind, record_id, study_id))
                    self.ui.tableWidget_participants.setCellWidget(row_ind,3,bt)

            self.ui.tableWidget_participants.resizeColumnsToContents()


        # populate mri session table and list
        self.ui.tableWidget_mri_sessions.clear()
        self.ui.tableWidget_mri_sessions.setColumnCount(12)
        self.ui.tableWidget_mri_sessions.setHorizontalHeaderLabels(("Date", "Time", "Session Description", "Subject ID", "De-identified ID", "Session ID", "Data Valid" , "IDs Validated", "Skip", "Data Converted", "", ""))

        self.ui.listWidget_mri_session_series.blockSignals(True)
        self.ui.listWidget_mri_session_series.clear()
        self.ui.listWidget_mri_session_series.setEnabled(False)
        
        if isinstance(mri_sessions,list):
            self.ui.tableWidget_mri_sessions.setRowCount(len(mri_sessions))
            row_ind = -1
            for session in mri_sessions:

                # parse session data
                record_id = session["id"]
                participant_id = session["participant_id"]
                participant_session_id = session["participant_session_id"]
                description = session["description"]
                data_recorded_date = session["data_recorded_date"]
                data_recorded_time = session["data_recorded_time"]
                data_recorded_dt = session["data_recorded_dt"]
                conversion_validated_dt = session["conversion_validated_dt"]
                conversion_validated_with_summary_dt = session["conversion_validated_with_summary_dt"]
                conversion_valid = session["conversion_valid"]
                study_id_validated_dt = session["study_id_validated_dt"]
                session_id_validated_dt = session["session_id_validated_dt"]
                skip_processing = session["skip_processing"]
                data_converted_dt = session["data_converted_dt"]
                row_ind = row_ind+1

                # get participant data
                study_id, deidentified_id, group_assignment = data_viewer_utils.get_participant_data_for_session(self, db, participant_id)

                # check if ID editing is allowed
                id_editing_allowed = data_converted_dt == None

                # check if ID validation is required
                id_validation_required = id_editing_allowed and ((study_id_validated_dt == None) or (session_id_validated_dt == None))

                # populate table
                self.ui.tableWidget_mri_sessions.setItem(row_ind,0,QTableWidgetItem(data_recorded_date))
                self.ui.tableWidget_mri_sessions.setItem(row_ind,1,QTableWidgetItem(data_recorded_time))
                self.ui.tableWidget_mri_sessions.setItem(row_ind,2,QTableWidgetItem(description))
                self.ui.tableWidget_mri_sessions.setItem(row_ind,3,QTableWidgetItem(study_id))
                self.ui.tableWidget_mri_sessions.setItem(row_ind,4,QTableWidgetItem(deidentified_id))
                self.ui.tableWidget_mri_sessions.setItem(row_ind,5,QTableWidgetItem(participant_session_id))
                self.ui.tableWidget_mri_sessions.setItem(row_ind,6,QTableWidgetItem("" if (conversion_valid == None) else ("Y" if (conversion_valid == 1) else "N")))
                self.ui.tableWidget_mri_sessions.setItem(row_ind,7,QTableWidgetItem("N" if id_validation_required else "Y"))
                self.ui.tableWidget_mri_sessions.setItem(row_ind,8,QTableWidgetItem("Y" if (skip_processing == 1) else "N"))
                self.ui.tableWidget_mri_sessions.setItem(row_ind,9,QTableWidgetItem("N" if (data_converted_dt == None) else "Y"))

                if conversion_valid!=1 and skip_processing!=1:
                    self.ui.tableWidget_mri_sessions.item(row_ind,6).setBackground(QColor(255,0,0))

                if skip_processing==1:
                    self.ui.tableWidget_mri_sessions.item(row_ind,8).setBackground(QColor(230,230,230))

                if data_converted_dt == None:
                    self.ui.tableWidget_mri_sessions.item(row_ind,9).setBackground(QColor(230,230,230))

                if id_validation_required:
                    bt = QPushButton("Validate")
                    bt.clicked.connect(partial(self.validate_mri_session_button_pressed,self.ui.tableWidget_mri_sessions, row_ind, record_id, description))
                    self.ui.tableWidget_mri_sessions.setCellWidget(row_ind,10,bt)

                    for j in range(self.ui.tableWidget_mri_sessions.columnCount()-2):
                        self.ui.tableWidget_mri_sessions.item(row_ind,j).setBackground(QColor(255,0,0))

                elif id_editing_allowed:
                    bt = QPushButton("Edit")
                    bt.clicked.connect(partial(self.edit_mri_session_button_pressed,self.ui.tableWidget_mri_sessions, row_ind, record_id, description))
                    self.ui.tableWidget_mri_sessions.setCellWidget(row_ind,10,bt)

                bt = QPushButton("Reprocess")
                bt.clicked.connect(partial(self.reprocess_mri_session_button_pressed,self.ui.tableWidget_mri_sessions, row_ind, record_id, description))
                self.ui.tableWidget_mri_sessions.setCellWidget(row_ind,11,bt)

                # add item to session list
                session_item = QListWidgetItem(data_recorded_date + " | " + description)
                session_item.setData(Qt.UserRole, record_id)
                self.ui.listWidget_mri_session_series.addItem(session_item)
                self.ui.listWidget_mri_session_series.setEnabled(True)
                self.ui.listWidget_mri_session_series.setCurrentRow(0)

            self.ui.tableWidget_mri_sessions.resizeColumnsToContents()

        # re-activate session list
        self.ui.listWidget_mri_session_series.blockSignals(False)
        
        # close connection to database
        db.close()

        # update series table
        self.update_session_series_table()

    def validate_mri_session_button_pressed(self,table=None, row=-1, id=None, description=""):

        # run validation dialog
        validate_dialog = edit_session_dialog(self, session_row_id=id, mode="validate", settings_database=self._settings_db, settings_study=self._settings_study, session_description=description)
        validate_dialog.exec()

        if validate_dialog.session_went_from_skipped_to_notskipped:
            self.reprocess_mri_session(id=id, description=description, action=1)
        
        # reload db
        self.load_db()

    def edit_mri_session_button_pressed(self,table=None, row=-1, id=None, description=""):

        # run editing dialog
        edit_dialog = edit_session_dialog(self, session_row_id=id, mode="edit", settings_database=self._settings_db, settings_study=self._settings_study, session_description=description)
        edit_dialog.exec()

        if edit_dialog.session_went_from_skipped_to_notskipped:
            self.reprocess_mri_session(id=id, description=description, action=1)
        
        # reload db
        self.load_db()

    def reprocess_mri_session(self, id=None, description="", action=None):

        # get session data
        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        session = db.get_mri_session_data(id=id, return_only_first=True)
        if (session == None) or (session == -1):
            res = QMessageBox.critical(self, "Data Viewer", "Unable to get MRI session data.")
            db.close()
            return
        
        # get action
        if action==None:
            # check if session data has already been converted
            if session["data_converted_dt"] != None:
                action = 1 # default to rerunning data download and processing
            else:
                # ask the user how they want to proceed
                reprocess_dialog = reprocess_session_dialog(self, session_description=description)
                res = reprocess_dialog.exec()
                if res==0:
                    db.close()
                    return
                
                action = reprocess_dialog.result_id
            ask_user_to_confirm = True
        else:
            ask_user_to_confirm = False

        # run selected action
        match action:
            case 0: # rerun data validation
                if ask_user_to_confirm:
                    res = QMessageBox.question(self,"Data Viewer","Validation scripts will be rerun for session " + description + " and all its series. Previous validation results will be discarded.\nPlease confirm")
                    if res != QMessageBox.Yes:
                        db.close()
                        return
                
                # get all series for this session
                session_series = db.get_mri_series_data(session_id=session["id"])
                if session_series == -1:
                    res = QMessageBox.critical(self,"Data Viewer","Could not get series for selected session.")
                    db.close()
                    return
                
                # clear validation results from series
                if (session_series!=None) and (len(session_series)>0):
                    for series in session_series:
                        db.clear_values_from_mri_series(series["id"], 
                                                        series_recorded_dt = True,
                                                        number_files = True,
                                                        files_validated_dt = True,
                                                        files_validated_with_summary_dt = True,
                                                        files_valid = True,
                                                        dcm2bids_criteria = True,
                                                        dcm2bids_criteria_in_config = True,
                                                        duplicate_series = True,
                                                        skip_processing = True)
                        
                # clear validation results from session
                db.clear_values_from_mri_session(session["id"],
                                                 conversion_validated_dt = True,
                                                 conversion_validated_with_summary_dt = True,
                                                 conversion_valid = True)
                
                db.commit()

            case 1: # rerun data download and processing
                if ask_user_to_confirm:
                    res = QMessageBox.question(self,"Data Viewer","Data of session " + description + " will be downloaded and processed again. Previously downloaded and processed data will be removed from the work directory.\nPlease confirm")
                    if res != QMessageBox.Yes:
                        db.close()
                        return
                
                # get all series for this session
                session_series = db.get_mri_series_data(session_id=session["id"])
                if session_series == -1:
                    res = QMessageBox.critical(self,"Data Viewer","Could not get series for selected session.")
                    db.close()
                    return

                # delete session data folder
                session_name = Path(session["data_file"]).stem
                session_dir = Path(self._settings_processing["mri"]["workdir"]).joinpath(session_name)
                if session_dir.exists():
                    shutil.rmtree(session_dir)

                # clear series from database
                if (session_series!=None) and (len(session_series)>0):
                    for series in session_series:
                        db.remove_mri_series(series["id"])
                        
                # clear results from session
                db.clear_values_from_mri_session(session["id"],
                                                 summary_file = True,
                                                 data_downloaded_dt = True,
                                                 notification_sent_dt = True,
                                                 summary_downloaded_dt = True,
                                                 converted_to_nifti_dt = True,
                                                 conversion_validated_dt = True,
                                                 conversion_validated_with_summary_dt = True,
                                                 conversion_valid = True,
                                                 data_converted_dt = True,
                                                 data_uploaded_dt = True)
                
                db.commit()                

        # close db
        db.close()

        # reload db
        self.load_db()

    def reprocess_mri_session_button_pressed(self,table=None, row=-1, id=None, description=""):
        self.reprocess_mri_session(id=id, description=description)

    def edit_participant_button_pressed(self,table=None, row=-1, id=None, study_id=""):

        # run editing dialog
        edit_dialog = edit_participant_dialog(self, participant_row_id=id, settings_database=self._settings_db, settings_study=self._settings_study, subject_id=study_id)
        edit_dialog.exec()
        
        # reload db
        self.load_db()

    def pushButton_new_participant_clicked(self):
        
        # check study config
        if (self._settings_study == None) or (self._settings_study == -1):
            return

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

        # reload db
        self.load_db()

    def update_session_series_table(self):

        # clear table
        self.ui.tableWidget_mri_series.clear()
        self.ui.tableWidget_mri_series.setColumnCount(0)
        self.ui.tableWidget_mri_series.setRowCount(0)

        # skip if session list is disabled
        if not self.ui.listWidget_mri_session_series.isEnabled():
            return
        
        # get selected session
        selected_session_description = self.ui.listWidget_mri_session_series.currentItem().text()
        selected_session_id = self.ui.listWidget_mri_session_series.currentItem().data(Qt.UserRole)
        
        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        # get session information
        session = db.get_mri_session_data(id=selected_session_id, return_only_first=True)

        # get series for this session
        session_series = db.get_mri_series_data(session_id=selected_session_id, sort_column="series_recorded_dt", sort_dir="ascending")
        
        # close database
        db.close()

        if (session == None) or (session == -1):
            res = QMessageBox.critical(self,"Data Viewer","Could not get data for selected session.")
            return

        if session_series == -1:
            res = QMessageBox.critical(self,"Data Viewer","Could not get series for selected session.")
            return
        if (session_series==None) or (len(session_series)<1):
            return
        
        # check if session data was already converted
        session_data_converted = session["data_converted_dt"] != None
        
        # set column names
        self.ui.tableWidget_mri_series.setColumnCount(11)
        self.ui.tableWidget_mri_series.setHorizontalHeaderLabels(("Series", "Date", "Time", "Series Description", "Files", "Files Valid", "dcm2bids Criteria Match", "Duplicates", "Skip", "Data Converted", ""))

        # populate series table
        self.ui.tableWidget_mri_series.setRowCount(len(session_series))
        row_ind = -1
        for series in session_series:

            series_number = series["series_number"]
            series_recorded_dt = series["series_recorded_dt"]
            description = series["description"]
            number_files = series["number_files"]
            files_valid = series["files_valid"]
            dcm2bids_criteria_in_config = series["dcm2bids_criteria_in_config"]
            duplicate_series = series["duplicate_series"]
            skip_processing = series["skip_processing"]
            data_converted_dt = series["data_converted_dt"]

            row_ind = row_ind+1

            # get date and time
            if series_recorded_dt != None:
                session_recorded_date = datetime.fromtimestamp(series_recorded_dt).strftime("%Y/%m/%d")
                session_recorded_time = datetime.fromtimestamp(series_recorded_dt).strftime("%H:%M:%S.%f")
            else:
                session_recorded_date = None
                session_recorded_time = None


            # add row
            self.ui.tableWidget_mri_series.setItem(row_ind,0,QTableWidgetItem("" if series_number== None else str(series_number)))
            self.ui.tableWidget_mri_series.setItem(row_ind,1,QTableWidgetItem(session_recorded_date))
            self.ui.tableWidget_mri_series.setItem(row_ind,2,QTableWidgetItem(session_recorded_time))
            self.ui.tableWidget_mri_series.setItem(row_ind,3,QTableWidgetItem(description))
            self.ui.tableWidget_mri_series.setItem(row_ind,4,QTableWidgetItem("" if number_files== None else str(number_files)))
            self.ui.tableWidget_mri_series.setItem(row_ind,5,QTableWidgetItem("Y" if files_valid==1 else "N"))
            self.ui.tableWidget_mri_series.setItem(row_ind,6,QTableWidgetItem("Y" if dcm2bids_criteria_in_config==1 else "N"))
            self.ui.tableWidget_mri_series.setItem(row_ind,7,QTableWidgetItem(duplicate_series))
            self.ui.tableWidget_mri_series.setItem(row_ind,8,QTableWidgetItem("Y" if skip_processing==1 else "N"))
            self.ui.tableWidget_mri_series.setItem(row_ind,9,QTableWidgetItem("N" if data_converted_dt==None else "Y"))

            # add skip and include buttons
            if (not session_data_converted) and (not data_converted_dt):
                if skip_processing==1:
                    bt = QPushButton("Include")
                    bt.clicked.connect(partial(self.skip_include_mri_series_button_pressed,self.ui.tableWidget_mri_series, row_ind, selected_session_id, series_number, False))
                    self.ui.tableWidget_mri_series.setCellWidget(row_ind,10,bt)
                else:
                    bt = QPushButton("Skip")
                    bt.clicked.connect(partial(self.skip_include_mri_series_button_pressed,self.ui.tableWidget_mri_series, row_ind, selected_session_id, series_number, True))
                    self.ui.tableWidget_mri_series.setCellWidget(row_ind,10,bt)

            # add color coding to show skipped and converted series
            if skip_processing==1:
                self.ui.tableWidget_mri_series.item(row_ind,8).setBackground(QColor(230,230,230))
            if data_converted_dt == None:
                self.ui.tableWidget_mri_series.item(row_ind,9).setBackground(QColor(230,230,230))

        self.ui.tableWidget_mri_series.resizeColumnsToContents()

    def skip_include_mri_series_button_pressed(self, table=None, row=-1, session_id=None, series_number=None, skip=False):

        # confirm with user
        if skip:
            res = QMessageBox.question(self,"Data Viewer","Series " + str(series_number) + " will be skipped.\nPlease confirm")
        else:
            res = QMessageBox.question(self,"Data Viewer","Series " + str(series_number) + " will be included.\nPlease confirm")
        if res != QMessageBox.Yes:
            return
        
        # connect to database
        db = database.db(self._settings_db["db_path"])
        db.n_default_query_attempts = self._settings_db["n_default_query_attempts"] # default number of attempts before a query fails (e.g. transactions could be blocked by another process writing to the database)

        # get series information
        series = db.get_mri_series_data(session_id=session_id, series_number=series_number, return_only_first=True)
        if (series == None) or (series == -1):
            res = QMessageBox.critical(self,"Data Viewer","Could not get series information.")
            db.close()
            return
        
        # run some additional checks if this series should be included
        duplicate_series_to_skip = []
        if not skip:
            # check if there are matching dcm2bids criteria in config file
            dcm2bids_criteria_in_config = series["dcm2bids_criteria_in_config"] == 1
            if not dcm2bids_criteria_in_config:
                res = QMessageBox.critical(self,"Data Viewer","Could not include series " + str(series_number) + " as there are no matching criteria in dcm2bids config. Please update the config file and validate this session again.")
                db.close()
                return

        
            # check if series has duplicates
            duplicate_series = []
            if (series["duplicate_series"] != None) and (series["duplicate_series"] != ""):
                duplicate_series = json.loads(series["duplicate_series"])

            duplicate_series_to_skip_str = ""
            for duplicate in duplicate_series:
                if duplicate!=series_number:
                    duplicate_series_to_skip.append(duplicate)
                    duplicate_series_to_skip_str = duplicate_series_to_skip_str + str(duplicate) + ", "
            if duplicate_series_to_skip_str != "":
                duplicate_series_to_skip_str = duplicate_series_to_skip_str[:-2]

            if len(duplicate_series_to_skip)>0:
                res = QMessageBox.question(self,"Data Viewer","Series " + str(series_number) + " has one or more duplicates with matching dcm2bids criteria. By including this series, the following series will be skipped: " + duplicate_series_to_skip_str + "\nPlease confirm")
                if res != QMessageBox.Yes:
                    db.close()
                    return
            

        # update series
        db.update_mri_series(series["id"], skip_processing=skip)
        
        # skip any additional series (duplicates)
        for series_number_to_skip in duplicate_series_to_skip:
            series_to_skip = db.get_mri_series_data(session_id=session_id, series_number=series_number_to_skip, return_only_first=True)
            if (series_to_skip == None) or (series_to_skip == -1):
                res = QMessageBox.critical(self,"Data Viewer","Could not get information for series " + str(series_number_to_skip) + ".")
                db.close()
                return
            db.update_mri_series(series_to_skip["id"], skip_processing=True)

        # commit changes and close database
        db.commit()
        db.close()        
        
        # reload db
        self.load_db()

        # reset session selection
        for index in range(self.ui.listWidget_mri_session_series.count()):
            item = self.ui.listWidget_mri_session_series.item(index)
            if item.data(Qt.UserRole)==session_id:
                self.ui.listWidget_mri_session_series.setCurrentItem(item)
                break

        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = data_viewer_ui()
    widget.show()
    sys.exit(app.exec())
