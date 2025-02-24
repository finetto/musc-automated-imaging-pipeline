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

from ui_reprocess_session_dialog import Ui_reprocess_session_dialog

class reprocess_session_dialog(QDialog):

    result = ""
    result_id = -1

    def __init__(self, parent=None, session_description=""):

        super().__init__(parent)
        self.ui = Ui_reprocess_session_dialog()
        self.ui.setupUi(self)

        self.setWindowTitle("Reprocess Session")

        # set session description
        if session_description == "":
            self.ui.label_session_description.setText("")
        else:
            self.ui.label_session_description.setText(session_description)

        # define connections to signals
        self.ui.pushButton_ok.clicked.connect(self.pushButton_ok_clicked)
        self.ui.pushButton_cancel.clicked.connect(self.pushButton_cancel_clicked)
        self.ui.buttonGroup_reprocess.idClicked.connect(self.radioButton_clicked)

        # disable ok button until selection is made
        self.ui.pushButton_ok.setEnabled(False)

        # set ids of radio buttons
        for index, button in enumerate(self.ui.buttonGroup_reprocess.buttons()):
            self.ui.buttonGroup_reprocess.setId(button,index)


    # save and exit
    def pushButton_ok_clicked(self):
        self.accept()

    # exit without saving
    def pushButton_cancel_clicked(self):
        self.result = "canceled"
        self.result_id = -1
        self.close()

    def radioButton_clicked(self, id):
        self.result_id = id
        self.result = self.ui.buttonGroup_reprocess.button(id).text()
        self.ui.pushButton_ok.setEnabled(True)