# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_participant_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLayout,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_edit_participant_dialog(object):
    def setupUi(self, edit_participant_dialog):
        if not edit_participant_dialog.objectName():
            edit_participant_dialog.setObjectName(u"edit_participant_dialog")
        edit_participant_dialog.setWindowModality(Qt.WindowModal)
        edit_participant_dialog.resize(395, 216)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(edit_participant_dialog.sizePolicy().hasHeightForWidth())
        edit_participant_dialog.setSizePolicy(sizePolicy)
        edit_participant_dialog.setModal(True)
        self.gridLayout = QGridLayout(edit_participant_dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.pushButton_ok = QPushButton(edit_participant_dialog)
        self.pushButton_ok.setObjectName(u"pushButton_ok")

        self.gridLayout.addWidget(self.pushButton_ok, 12, 2, 1, 1)

        self.groupBox_description = QGroupBox(edit_participant_dialog)
        self.groupBox_description.setObjectName(u"groupBox_description")
        self.horizontalLayout = QHBoxLayout(self.groupBox_description)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setSizeConstraint(QLayout.SetNoConstraint)
        self.label_5 = QLabel(self.groupBox_description)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout.addWidget(self.label_5)

        self.label_subject_id = QLabel(self.groupBox_description)
        self.label_subject_id.setObjectName(u"label_subject_id")
        font = QFont()
        font.setBold(True)
        self.label_subject_id.setFont(font)

        self.horizontalLayout.addWidget(self.label_subject_id)

        self.horizontalLayout.setStretch(0, 1)
        self.horizontalLayout.setStretch(1, 2)

        self.gridLayout.addWidget(self.groupBox_description, 7, 0, 1, 3)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 8, 0, 1, 1)

        self.pushButton_cancel = QPushButton(edit_participant_dialog)
        self.pushButton_cancel.setObjectName(u"pushButton_cancel")

        self.gridLayout.addWidget(self.pushButton_cancel, 12, 1, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 12, 0, 1, 1)

        self.groupBox_participant = QGroupBox(edit_participant_dialog)
        self.groupBox_participant.setObjectName(u"groupBox_participant")
        self.gridLayout_2 = QGridLayout(self.groupBox_participant)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_2 = QLabel(self.groupBox_participant)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 0, 0, 1, 1)

        self.label_3 = QLabel(self.groupBox_participant)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_2.addWidget(self.label_3, 1, 0, 1, 1)

        self.lineEdit_deidentified_id = QLineEdit(self.groupBox_participant)
        self.lineEdit_deidentified_id.setObjectName(u"lineEdit_deidentified_id")

        self.gridLayout_2.addWidget(self.lineEdit_deidentified_id, 0, 1, 1, 1)

        self.comboBox_group_assignment = QComboBox(self.groupBox_participant)
        self.comboBox_group_assignment.setObjectName(u"comboBox_group_assignment")

        self.gridLayout_2.addWidget(self.comboBox_group_assignment, 1, 1, 1, 1)

        self.pushButton_generate_deidentifdied_id = QPushButton(self.groupBox_participant)
        self.pushButton_generate_deidentifdied_id.setObjectName(u"pushButton_generate_deidentifdied_id")

        self.gridLayout_2.addWidget(self.pushButton_generate_deidentifdied_id, 0, 2, 1, 1)


        self.gridLayout.addWidget(self.groupBox_participant, 10, 0, 1, 3)


        self.retranslateUi(edit_participant_dialog)

        QMetaObject.connectSlotsByName(edit_participant_dialog)
    # setupUi

    def retranslateUi(self, edit_participant_dialog):
        edit_participant_dialog.setWindowTitle(QCoreApplication.translate("edit_participant_dialog", u"Dialog", None))
        self.pushButton_ok.setText(QCoreApplication.translate("edit_participant_dialog", u"OK", None))
        self.groupBox_description.setTitle("")
        self.label_5.setText(QCoreApplication.translate("edit_participant_dialog", u"Subject ID:", None))
        self.label_subject_id.setText(QCoreApplication.translate("edit_participant_dialog", u"TextLabel", None))
        self.pushButton_cancel.setText(QCoreApplication.translate("edit_participant_dialog", u"Cancel", None))
        self.groupBox_participant.setTitle("")
        self.label_2.setText(QCoreApplication.translate("edit_participant_dialog", u"De-identified ID", None))
        self.label_3.setText(QCoreApplication.translate("edit_participant_dialog", u"Group assignment", None))
        self.pushButton_generate_deidentifdied_id.setText(QCoreApplication.translate("edit_participant_dialog", u"Generate", None))
    # retranslateUi

