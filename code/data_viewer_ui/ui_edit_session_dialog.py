# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_session_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLayout, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_edit_session_dialog(object):
    def setupUi(self, edit_session_dialog):
        if not edit_session_dialog.objectName():
            edit_session_dialog.setObjectName(u"edit_session_dialog")
        edit_session_dialog.setWindowModality(Qt.WindowModal)
        edit_session_dialog.resize(395, 310)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(edit_session_dialog.sizePolicy().hasHeightForWidth())
        edit_session_dialog.setSizePolicy(sizePolicy)
        edit_session_dialog.setModal(True)
        self.gridLayout = QGridLayout(edit_session_dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.pushButton_ok = QPushButton(edit_session_dialog)
        self.pushButton_ok.setObjectName(u"pushButton_ok")

        self.gridLayout.addWidget(self.pushButton_ok, 13, 2, 1, 1)

        self.groupBox_participant = QGroupBox(edit_session_dialog)
        self.groupBox_participant.setObjectName(u"groupBox_participant")
        self.gridLayout_2 = QGridLayout(self.groupBox_participant)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_3 = QLabel(self.groupBox_participant)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_2.addWidget(self.label_3, 2, 0, 1, 1)

        self.comboBox_subject_id = QComboBox(self.groupBox_participant)
        self.comboBox_subject_id.setObjectName(u"comboBox_subject_id")

        self.gridLayout_2.addWidget(self.comboBox_subject_id, 0, 1, 1, 1)

        self.label_2 = QLabel(self.groupBox_participant)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)

        self.lineEdit_deidentified_id = QLineEdit(self.groupBox_participant)
        self.lineEdit_deidentified_id.setObjectName(u"lineEdit_deidentified_id")

        self.gridLayout_2.addWidget(self.lineEdit_deidentified_id, 1, 1, 1, 1)

        self.label = QLabel(self.groupBox_participant)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.comboBox_group_assignment = QComboBox(self.groupBox_participant)
        self.comboBox_group_assignment.setObjectName(u"comboBox_group_assignment")

        self.gridLayout_2.addWidget(self.comboBox_group_assignment, 2, 1, 1, 1)

        self.pushButton_new_subject_id = QPushButton(self.groupBox_participant)
        self.pushButton_new_subject_id.setObjectName(u"pushButton_new_subject_id")

        self.gridLayout_2.addWidget(self.pushButton_new_subject_id, 0, 2, 1, 1)

        self.pushButton_generate_deidentifdied_id = QPushButton(self.groupBox_participant)
        self.pushButton_generate_deidentifdied_id.setObjectName(u"pushButton_generate_deidentifdied_id")

        self.gridLayout_2.addWidget(self.pushButton_generate_deidentifdied_id, 1, 2, 1, 1)


        self.gridLayout.addWidget(self.groupBox_participant, 10, 0, 1, 3)

        self.groupBox_description = QGroupBox(edit_session_dialog)
        self.groupBox_description.setObjectName(u"groupBox_description")
        self.horizontalLayout = QHBoxLayout(self.groupBox_description)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setSizeConstraint(QLayout.SetNoConstraint)
        self.label_5 = QLabel(self.groupBox_description)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout.addWidget(self.label_5)

        self.label_session_description = QLabel(self.groupBox_description)
        self.label_session_description.setObjectName(u"label_session_description")
        font = QFont()
        font.setBold(True)
        self.label_session_description.setFont(font)

        self.horizontalLayout.addWidget(self.label_session_description)

        self.horizontalLayout.setStretch(0, 1)
        self.horizontalLayout.setStretch(1, 2)

        self.gridLayout.addWidget(self.groupBox_description, 7, 0, 1, 3)

        self.groupBox_session = QGroupBox(edit_session_dialog)
        self.groupBox_session.setObjectName(u"groupBox_session")
        self.groupBox_session.setEnabled(True)
        self.gridLayout_3 = QGridLayout(self.groupBox_session)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label_4 = QLabel(self.groupBox_session)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_3.addWidget(self.label_4, 0, 0, 1, 1)

        self.checkBox_skip_processing = QCheckBox(self.groupBox_session)
        self.checkBox_skip_processing.setObjectName(u"checkBox_skip_processing")

        self.gridLayout_3.addWidget(self.checkBox_skip_processing, 1, 0, 1, 1)

        self.session_id_placeholder = QHBoxLayout()
        self.session_id_placeholder.setObjectName(u"session_id_placeholder")

        self.gridLayout_3.addLayout(self.session_id_placeholder, 0, 1, 1, 1)


        self.gridLayout.addWidget(self.groupBox_session, 11, 0, 1, 3)

        self.pushButton_cancel = QPushButton(edit_session_dialog)
        self.pushButton_cancel.setObjectName(u"pushButton_cancel")

        self.gridLayout.addWidget(self.pushButton_cancel, 13, 1, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 13, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 8, 0, 1, 1)


        self.retranslateUi(edit_session_dialog)

        QMetaObject.connectSlotsByName(edit_session_dialog)
    # setupUi

    def retranslateUi(self, edit_session_dialog):
        edit_session_dialog.setWindowTitle(QCoreApplication.translate("edit_session_dialog", u"Dialog", None))
        self.pushButton_ok.setText(QCoreApplication.translate("edit_session_dialog", u"OK", None))
        self.groupBox_participant.setTitle(QCoreApplication.translate("edit_session_dialog", u"Participant", None))
        self.label_3.setText(QCoreApplication.translate("edit_session_dialog", u"Group assignment", None))
        self.label_2.setText(QCoreApplication.translate("edit_session_dialog", u"De-identified ID", None))
        self.label.setText(QCoreApplication.translate("edit_session_dialog", u"Subject ID", None))
        self.pushButton_new_subject_id.setText(QCoreApplication.translate("edit_session_dialog", u"New", None))
        self.pushButton_generate_deidentifdied_id.setText(QCoreApplication.translate("edit_session_dialog", u"Generate", None))
        self.groupBox_description.setTitle("")
        self.label_5.setText(QCoreApplication.translate("edit_session_dialog", u"Description:", None))
        self.label_session_description.setText(QCoreApplication.translate("edit_session_dialog", u"TextLabel", None))
        self.groupBox_session.setTitle(QCoreApplication.translate("edit_session_dialog", u"Session", None))
        self.label_4.setText(QCoreApplication.translate("edit_session_dialog", u"Session ID", None))
        self.checkBox_skip_processing.setText(QCoreApplication.translate("edit_session_dialog", u"Skip processing", None))
        self.pushButton_cancel.setText(QCoreApplication.translate("edit_session_dialog", u"Cancel", None))
    # retranslateUi

